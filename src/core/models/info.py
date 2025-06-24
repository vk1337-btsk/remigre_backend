from sqlalchemy import Integer, Column, String, Text

from src.core.models.base_models import AbstractBaseModel


class InfoModel(AbstractBaseModel):

    __tablename__ = "info"

    __table_args__ = {"comment": "Таблица с данными для заполнения сайта"}

    id = Column(Integer, primary_key=True, index=True, comment="ID записи")
    slug = Column(String, nullable=False, index=True, unique=True, comment="Название раздела")
    description = Column(Text, nullable=False, comment="Описание раздела")
