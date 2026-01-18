import logging
from typing import Any, Optional, Sequence

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    and_,
    cast,
    func,
    or_,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.models_and_mixins import AbstractBaseModel, CreatedUpdatedAtMixin


class ProfessionsModel(AbstractBaseModel, CreatedUpdatedAtMixin):

    __tablename__ = "data_professions"

    __table_args__ = ({"comment": "Справочник профессий"},)

    id = Column(Integer, primary_key=True, index=True, comment="ID")

    # Основные данные
    name = Column(String(255), nullable=False, comment="Название")
    name_eng = Column(String(255), nullable=False, comment="Название ENG")
    description = Column(Text, nullable=True, comment="Описание")

    # Дополнительно
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"), comment="Флаг активности")
    add_info = Column(JSONB, nullable=True, comment="Доп. информация")
