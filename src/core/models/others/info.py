import logging

from sqlalchemy import Column, Integer, String, Text

from src.core.models.base_and_mixins import AbstractBaseModel, CreatedUpdatedAtMixin


logger = logging.getLogger(__name__)


class InfoModel(AbstractBaseModel, CreatedUpdatedAtMixin):

    __tablename__ = "info"

    __table_args__ = {"comment": "Таблица с данными для заполнения сайта"}

    id = Column(Integer, primary_key=True, index=True, comment="ID записи")
    slug = Column(String, nullable=False, index=True, unique=True, comment="Название раздела")
    description = Column(Text, nullable=False, comment="Описание раздела")
