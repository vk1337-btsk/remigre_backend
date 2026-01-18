# src\core\database\database.py
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings


"""Основные настройки для работы с асинхронной БД 
(движок, фабрика сессий, Зависимость (Dependency) для получения сессии)"""

async_engine = create_async_engine(
    url=settings.db.url_async.get_secret_value(),
    echo=settings.db.db_echo,
    pool_pre_ping=True,
    pool_recycle=3600,
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_async_session_factory():
    """Фабрика сессий"""

    return AsyncSessionLocal
