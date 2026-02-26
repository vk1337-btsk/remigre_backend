from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text

from src.core.models.base_and_mixins import AbstractBaseModel, CreatedUpdatedAtMixin


class MetricPresetModel(AbstractBaseModel, CreatedUpdatedAtMixin):

    __tablename__ = "metric_preset"
    __table_args__ = (
        UniqueConstraint("metric_id", "slug", name="metric_preset_metric_id_slug_key"),
        Index("idx_preset_metric", "metric_id"),
        Index("idx_preset_slug", "slug"),
        Index(
            "idx_preset_country_list",
            "metric_id",
            "display_priority",
            postgresql_where=text("for_country_list AND is_active"),
        ),
        Index(
            "idx_preset_city_list",
            "metric_id",
            "display_priority",
            postgresql_where=text("for_city_list AND is_active"),
        ),
        Index(
            "idx_preset_country_detail",
            "metric_id",
            "display_priority",
            postgresql_where=text("for_country_detail AND is_active"),
        ),
        Index(
            "idx_preset_city_detail",
            "metric_id",
            "display_priority",
            postgresql_where=text("for_city_detail AND is_active"),
        ),
        Index("idx_preset_filter_criteria", "filter_criteria", postgresql_using="gin"),
        Index("idx_preset_period_spec", "period_spec", postgresql_using="gin"),
        Index("idx_preset_series", "series_id", postgresql_where=text("series_id IS NOT NULL")),
        {"comment": "Пресеты для быстрого доступа к определённым значениям метрик в различных контекстах"},
    )

    id = Column(Integer, primary_key=True)
    metric_id = Column(Integer, ForeignKey("metric_info.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False)
    description = Column(Text)

    filter_criteria = Column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="JSON с условиями для отбора серии (например, атрибуты)",
    )
    period_spec = Column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment='Спецификация периода: например, {"type":"latest", "period_type":"year"} или {"type":"fixed","year":2023}',
    )
    metadata_criteria = Column(
        JSONB, server_default=text("'{}'::jsonb"), comment="Критерии для фильтрации по метаданным серии (опционально)"
    )

    for_country_list = Column(Boolean, default=False)
    for_city_list = Column(Boolean, default=False)
    for_country_detail = Column(Boolean, default=False)
    for_city_detail = Column(Boolean, default=False)

    display_priority = Column(Integer, default=0)

    series_id = Column(
        Integer,
        ForeignKey("metric_series.id", ondelete="SET NULL"),
        comment="Кэшированный ID серии, соответствующей filter_criteria (заполняется для оптимизации)",
    )

    is_active = Column(Boolean, default=True)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.current_timestamp())
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )

    # Отношения — исправляем имена классов
    metric = relationship("MetricInfoModel", back_populates="presets")
    series = relationship("MetricSeriesModel", back_populates="presets")

    def __repr__(self):
        return f"<MetricPreset(id={self.id}, name='{self.name}', slug='{self.slug}')>"
