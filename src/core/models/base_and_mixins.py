from sqlalchemy import Column, DateTime, func
from sqlalchemy.orm import DeclarativeBase


# --------------- Основные абстрактные модели ---------------
class AbstractBaseModel(DeclarativeBase):
    """Базовый класс для всех моделей приложения."""

    __abstract__ = True

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


# --------------- Миксины ---------------
class CreatedUpdatedAtMixin:
    """Миксин для полей created_at и updated_at"""

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="Дата создания")

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Дата обновления",
    )
