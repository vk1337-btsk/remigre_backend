from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.core.config import settings


"""Основные настройки для работы с асинхронной БД 
(движок, фабрика сессий, Зависимость (Dependency) для получения сессии)"""

async_engine = create_async_engine(
    url=settings.db.db_url_async.get_secret_value(),
    echo=settings.db.db_echo,
    pool_pre_ping=True,
    pool_recycle=3600,
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_async_session():
    async with AsyncSessionLocal() as session:
        yield session


"""Основные настройки для работы с синхронной БД 
(движок, фабрика сессий, Зависимость (Dependency) для получения сессии)"""

sync_engine = create_engine(url=settings.db.db_url_sync.get_secret_value(), echo=settings.db.db_echo)
SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)


def get_sync_session():
    with SyncSessionLocal() as session:
        yield session
