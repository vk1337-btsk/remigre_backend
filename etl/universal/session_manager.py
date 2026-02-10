# etl/universal/session_manager.py
"""
Менеджер сессий для ETL с поддержкой SSH-туннелей
"""
import logging
import warnings
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from cryptography.utils import CryptographyDeprecationWarning
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings
from src.core.services.ssh_service import ssh_manager


warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)
logger = logging.getLogger(__name__)


class SessionManager:
    """Менеджер сессий базы данных для ETL с поддержкой SSH"""

    def __init__(self, database_url: Optional[str] = None):
        """Инициализация менеджера сессий"""
        self.database_url = database_url
        self.engine: Optional[AsyncEngine] = None
        self.async_session_factory: Optional[async_sessionmaker] = None
        self._ssh_tunnel_needed = not settings.is_project
        self._tunnel_started_by_us = False

    async def initialize(self):
        """Инициализация движка и фабрики сессий"""

        if not self.engine:
            # Определяем хост и порт для подключения
            db_host = settings.db.db_host
            db_port = settings.db.db_port

            # Если нужен SSH-туннель
            if self._ssh_tunnel_needed:
                try:
                    # Используем общий менеджер туннеля
                    if not ssh_manager.is_active():
                        logger.info("[SSH]: Запускаем SSH-туннель для ETL...")
                        ports = ssh_manager.start_tunnel(
                            ssh_host=settings.ssh.host,
                            ssh_port=settings.ssh.port,
                            ssh_user=settings.ssh.user,
                            ssh_key_path=settings.ssh.key_path,
                            addresses={
                                "postgresql": ("127.0.0.1", 65432),
                            },
                        )
                        self._tunnel_started_by_us = True
                    else:
                        logger.info("[SSH]: Используем существующий SSH-туннель")
                        ports = ssh_manager.get_ports()

                    db_host = "127.0.0.1"
                    db_port = ports.get("postgresql", db_port)
                    logger.info(f"[SSH]: Используем локальный порт для БД: {db_port}")

                except Exception as e:
                    logger.error(f"[SSH]: Не удалось запустить/получить туннель: {e}")
                    logger.warning("[SSH]: Пробуем подключиться напрямую...")

            # Формируем URL для подключения
            if not self.database_url:
                self.database_url = (
                    f"postgresql+asyncpg://"
                    f"{settings.db.db_user}:"
                    f"{settings.db.db_password.get_secret_value()}"
                    f"@{db_host}:{db_port}/{settings.db.db_name}"
                )

            # Создаем движок
            logger.info(f"Создание async engine для {db_host}:{db_port}")

            self.engine = create_async_engine(
                self.database_url,
                echo=settings.db.db_echo,
                pool_size=20,
                max_overflow=30,
                pool_pre_ping=True,
                pool_recycle=3600,
                connect_args={
                    "server_settings": {
                        "statement_timeout": "300000",
                        "application_name": "etl_processor_bulk",
                        "jit": "off",  # Важно для bulk insert
                    },
                },
            )

            self.async_session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )

            # Проверяем подключение
            await self._test_connection()

    async def _test_connection(self):
        """Проверка подключения к базе данных"""
        try:
            assert self.engine is not None

            async with self.engine.connect():
                pass
            logger.info("✅ Подключение к БД успешно установлено")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к БД: {e}")
            raise

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Получение сессии"""

        if not self.async_session_factory:
            await self.initialize()

        assert self.async_session_factory is not None

        async with self.async_session_factory() as session:
            try:
                yield session

            except Exception as e:
                await session.rollback()
                logger.error(f"Ошибка в сессии: {e}")
                raise
            finally:
                await session.close()

    async def close(self):
        """Закрытие соединений и остановка туннеля (если запускали мы)"""

        if self.engine:
            logger.info("Закрытие движка БД...")
            await self.engine.dispose()
            self.engine = None
            self.async_session_factory = None

        # Останавливаем SSH-туннель, только если мы его запускали
        if self._tunnel_started_by_us:
            ssh_manager.stop_tunnel()
            self._tunnel_started_by_us = False


# Глобальный экземпляр менеджера сессий
session_manager = SessionManager()
