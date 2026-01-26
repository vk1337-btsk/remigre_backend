# src\core\dependency.py
import secrets
from typing import AsyncGenerator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.config import settings


# ============ Зависимости для взаимодействия с БД ============
def get_sessionmaker(request: Request) -> async_sessionmaker[AsyncSession]:
    """Возвращает фабрику сессий для параллельного использования"""

    return request.app.state.sessionmaker


async def get_async_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Возвращает одну сессию для атомарных операций"""

    async with request.app.state.sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ============ Зависимости авторизации на странице документации ============
security = HTTPBasic()


def verify_docs_auth(credentials: HTTPBasicCredentials = Depends(security)):

    correct_username = secrets.compare_digest(credentials.username, settings.project.docs_username)
    correct_password = secrets.compare_digest(credentials.password, settings.project.docs_password)

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
