from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, text
from sqlalchemy.orm import DeclarativeBase


# --------------- Основные абстрактные модели ---------------
class AbstractBaseModel(DeclarativeBase):
    """Базовый класс для всех моделей приложения."""

    __abstract__ = True

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


class CreatedUpdatedAtMixin:
    """Миксин для полей created_at и updated_at"""

    created_at = Column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="Дата создания",
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="Дата обновления",
    )
