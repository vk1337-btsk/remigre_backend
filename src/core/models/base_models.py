from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, text
from sqlalchemy.orm import DeclarativeBase


# --------------- Основные абстрактные модели ---------------
class AbstractBaseModel(DeclarativeBase):
    """Базовый класс для всех моделей приложения."""

    __abstract__ = True

    id = Column(Integer, primary_key=True)

    created_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="Дата создания",
    )

    updated_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="Дата обновления",
    )

    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>"

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
