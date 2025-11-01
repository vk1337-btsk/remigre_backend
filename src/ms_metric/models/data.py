import logging

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from src.core.database.base_models import AbstractBaseModel


logger = logging.getLogger(__name__)


class MetricDataModel(AbstractBaseModel):
    """Модель, отражающая сырые данные метрик."""

    __tablename__ = "metric_data"

    __table_args__ = (
        UniqueConstraint(
            "metric_id", "period_id", "country_id", "city_id", name="uq_metric_data_unique_metric_period_location"
        ),
        CheckConstraint(
            "(city_id IS NOT NULL) OR (country_id IS NOT NULL)", name="ck_metric_data_city_or_country_not_null"
        ),
        # Ограничение: в диапазоне range_max больше range_min
        CheckConstraint(
            "(value_range_min IS NULL OR value_range_max IS NULL) OR (value_range_min <= value_range_max)",
            name="ck_metric_data_range_min_lte_max",
        ),
        # Ограничение: заполнен ровно один тип значения из всех возможных
        CheckConstraint(
            """
            (
                (CASE WHEN value_int IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN value_float IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN value_range_min IS NOT NULL OR value_range_max IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN value_bool IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN value_string IS NOT NULL THEN 1 ELSE 0 END)
            ) = 1
            """,
            name="ck_metric_data_only_one_value_filled",
        ),
        {"comment": "Таблица с данными метрик"},
    )

    id = Column(Integer, primary_key=True, index=True, comment="ID значения")

    # Связь с метриками
    metric_id = Column(
        Integer, ForeignKey("metric_info.id", ondelete="CASCADE"), nullable=False, index=True, comment="ID метрики"
    )
    period_id = Column(
        Integer, ForeignKey("metric_period.id", ondelete="CASCADE"), nullable=False, index=True, comment="ID периода"
    )

    # Связь с локациями
    country_id = Column(
        Integer, ForeignKey("country.id", ondelete="CASCADE"), nullable=True, index=True, comment="ID страны"
    )
    city_id = Column(Integer, ForeignKey("city.id", ondelete="CASCADE"), nullable=True, index=True, comment="ID города")

    # Значение метрики
    value_int = Column(Integer, nullable=True, index=True, comment="Значение в формате INT/NUMERIC")
    value_string = Column(String(255), nullable=True, comment="Значение в формате STRING")
    value_float = Column(Float, nullable=True, index=True, comment="Значение в формате FLOAT")
    value_range_min = Column(Integer, nullable=True, index=True, comment="Значение в формате MIN RANGE")
    value_range_max = Column(Integer, nullable=True, index=True, comment="Значение в формате MAX RANGE")
    value_bool = Column(Boolean, nullable=True, comment="Значение в формате BOOL")

    # Обратная связь
    metric = relationship("MetricModel", back_populates="data", lazy="selectin", foreign_keys=[metric_id])
    period = relationship("MetricPeriodModel", back_populates="data_entries", lazy="selectin", foreign_keys=[period_id])
    country = relationship("CountryModel", back_populates="data_entries", lazy="selectin", foreign_keys=[country_id])
    city = relationship("CityModel", back_populates="data_entries", lazy="selectin", foreign_keys=[city_id])
