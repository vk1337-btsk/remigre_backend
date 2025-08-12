import logging

from sqlalchemy import Boolean, Column, Enum, Integer, String, Text, text
from sqlalchemy.orm import relationship

from src.core.database.base_models import AbstractBaseModel
from src.core.enums import CategoryMetricEnum, TypeDataEnum
import src.core.database.models_init


logger = logging.getLogger(__name__)


class MetricModel(AbstractBaseModel):
    """Модель категории метрики"""

    __tablename__ = "metric_info"

    __table_args__ = ({"comment": "Информация об используемых метриках"},)

    id = Column(Integer, primary_key=True, index=True, comment="ID метрики")

    # Название и описание метрики
    slug = Column(
        String(255), nullable=False, index=True, unique=True, comment="Slug метрики (нужен как текстовой идентификатор)"
    )
    name = Column(String(255), nullable=False, comment="Название метрики")
    description = Column(Text, nullable=True, comment="Описание метрики")
    category = Column(Enum(CategoryMetricEnum), nullable=False, comment="Категория метрики")

    # Характеристики метрики
    source_name = Column(String(255), nullable=True, comment="Название источника метрики")
    source_url = Column(String(255), nullable=True, comment="URL источника метрики")
    type_data = Column(Enum(TypeDataEnum), nullable=False, comment="Тип данных метрики (int/str/range/bool)")
    unit_format = Column(String(255), nullable=False, comment="Единица измерения метрики")

    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"), comment="Активность метрики")

    # Обратная связь
    data = relationship("MetricDataModel", back_populates="metric", lazy="selectin", cascade="all, delete-orphan")
    periods = relationship("MetricPeriodModel", back_populates="metric", lazy="selectin", cascade="all, delete-orphan")
