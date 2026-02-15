from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from src.core.database.models_and_mixins import AbstractBaseModel, CreatedUpdatedAtMixin


class MetricDataNewModel(AbstractBaseModel, CreatedUpdatedAtMixin):
    """Модель данных метрик (новая структура)"""

    __tablename__ = "metric_data_new"

    __table_args__ = (
        UniqueConstraint(
            "series_id",
            "period_id",
            "country_id",
            "city_id",
            name="metric_data_new_series_id_period_id_country_id_city_id_key",
        ),
        CheckConstraint(
            """
            ((country_id IS NOT NULL) AND (city_id IS NULL)) OR 
            ((country_id IS NULL) AND (city_id IS NOT NULL))
            """,
            name="check_geography",
        ),
        CheckConstraint(
            """
            ((value_range_start IS NULL) AND (value_range_end IS NULL)) OR 
            (value_range_start <= value_range_end)
            """,
            name="check_range",
        ),
        CheckConstraint(
            """
            (
                (CASE WHEN value_numeric IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN value_string IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN value_boolean IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN (value_range_start IS NOT NULL) OR (value_range_end IS NOT NULL) THEN 1 ELSE 0 END)
            ) = 1
            """,
            name="check_single_value",
        ),
        Index("idx_data_series", "series_id"),
        Index("idx_data_period", "period_id"),
        Index("idx_data_country", "country_id"),
        Index("idx_data_city", "city_id"),
        Index("idx_data_country_metric_period", "country_id", "series_id", "period_id"),
        Index("idx_data_numeric", "value_numeric", postgresql_where=text("value_numeric IS NOT NULL")),
        {
            "comment": "Данные метрик (обновленная схема) - содержит фактические значения показателей для конкретных периодов и географических объектов"
        },
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Уникальный идентификатор записи данных")

    # Связи
    series_id = Column(
        Integer,
        ForeignKey("metric_series_new.id", name="metric_data_new_series_id_fkey", ondelete="CASCADE"),
        nullable=True,
        comment="Ссылка на серию данных",
    )

    period_id = Column(
        Integer, ForeignKey("metric_period_new.id", ondelete="CASCADE"), nullable=True, comment="Ссылка на период"
    )

    country_id = Column(
        Integer,
        ForeignKey("loc_country.id", name="metric_data_new_country_id_fkey", ondelete="CASCADE"),
        nullable=True,
        comment="Ссылка на страну",
    )

    city_id = Column(
        Integer,
        ForeignKey("loc_city.id", name="metric_data_new_city_id_fkey", ondelete="CASCADE"),
        nullable=True,
        comment="Ссылка на город",
    )

    # Значения (только одно поле должно быть заполнено)
    value_numeric = Column(Numeric(asdecimal=True), nullable=True, comment="Числовое значение показателя")

    value_string = Column(String(500), nullable=True, comment="Строковое значение показателя (макс. 500 символов)")

    value_boolean = Column(Boolean, nullable=True, comment="Булево значение показателя")

    value_range_start = Column(
        Numeric, nullable=True, comment="Начало диапазона значения (если значение представлено диапазоном)"
    )

    value_range_end = Column(
        Numeric, nullable=True, comment="Конец диапазона значения (если значение представлено диапазоном)"
    )

    # Метаданные
    meta_data = Column(JSONB, default=None, nullable=True, comment="Метаданные записи данных в формате JSON")

    # Связи
    series = relationship("MetricSeriesNewModel", back_populates="data")
    period = relationship("MetricPeriodNewModel", back_populates="data_entries")
    country = relationship("CountryModel", back_populates="metric_data")
    city = relationship("CityModel", back_populates="metric_data")

    def __repr__(self):
        return f"<MetricDataNewModel(id={self.id}, series={self.series_id}, period={self.period_id})>"
