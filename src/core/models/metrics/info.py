from sqlalchemy import (
    Boolean,
    Column,
    Enum,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from src.core.enums import CategoryMetricEnum, TypeDataEnum
from src.core.models.base_and_mixins import AbstractBaseModel, CreatedUpdatedAtMixin


class MetricInfoModel(AbstractBaseModel, CreatedUpdatedAtMixin):
    """Модель метрики"""

    __tablename__ = "metric_info"

    __table_args__ = (
        UniqueConstraint("slug", name="uq_metric_info_slug"),
        Index("idx_metric_info_category", "category"),
        Index("idx_metric_info_slug", "slug"),
        Index("idx_metric_info_is_active", "is_active"),
        {"comment": "Метрики"},
    )

    id = Column(Integer, primary_key=True, comment="ID метрики")
    slug = Column(String(255), nullable=False, comment="Уникальный SLUG")
    name = Column(String(255), nullable=False, comment="Название")
    description = Column(Text, nullable=True, comment="Описание")
    category = Column(
        Enum(CategoryMetricEnum, name="category_metric_enum", schema="public"),
        nullable=False,
        comment="Категория",
    )
    source_name = Column(String(255), nullable=True, comment="Название источника данных")
    source_url = Column(String(512), nullable=True, comment="URL источника данных")
    data_type = Column(
        Enum(TypeDataEnum, name="type_data_enum", schema="public"),
        nullable=False,
        comment="Тип данных метрики (ENUM: STRING, FLOAT, RANGE, BOOL)",
    )
    meta_data = Column(
        JSONB,
        nullable=True,
        comment="Метаданные в формате JSON (NULL - нет данных, JSON - есть данные)",
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=True,
        comment="Активна ли метрика (true - отображается, false - скрыта)",
    )

    # Связи
    series = relationship("MetricSeriesModel", back_populates="metric", cascade="all, delete-orphan")
    presets = relationship("MetricPresetModel", back_populates="metric", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MetricInfoModel(id={self.id}, name='{self.name}', slug='{self.slug}')>"
