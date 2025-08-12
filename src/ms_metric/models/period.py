import logging

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

import src.core.database.models_init
from src.core.database.base_models import AbstractBaseModel
from src.core.enums import PeriodTypeEnum


logger = logging.getLogger(__name__)


class MetricPeriodModel(AbstractBaseModel):
    """Модель периодов метрик"""

    __tablename__ = "metric_period"

    __table_args__ = (
        CheckConstraint("(period_year IS NULL) OR (period_year >= 0)", name="ck_period_year_nonnegative"),
        CheckConstraint("(period_month IS NULL) OR (period_month BETWEEN 1 AND 12)", name="ck_period_month_range"),
        CheckConstraint("(period_week IS NULL) OR (period_week BETWEEN 1 AND 55)", name="ck_period_week_range"),
        {"comment": "Временной промежуток метрики (версия)"},
    )
    id = Column(Integer, primary_key=True, index=True, comment="ID периода")

    # Связь с метрикой
    metric_id = Column(
        Integer, ForeignKey("metric_info.id", ondelete="CASCADE"), nullable=False, index=True, comment="ID метрики"
    )

    # Период
    period_type = Column(Enum(PeriodTypeEnum), nullable=False, index=True, comment="Тип периода метрики")
    period_year = Column(Integer, nullable=True, index=True, comment="Год (если указано)")
    period_month = Column(Integer, nullable=True, index=True, comment="Месяц (если указано)")
    period_week = Column(Integer, nullable=True, index=True, comment="Неделя (если указано)")

    # Интервал
    date_start = Column(DateTime, nullable=True, comment="Начало периода (для интервала)")
    date_end = Column(DateTime, nullable=True, comment="Конец периода (для интервала)")

    # Информация о получении данных
    collected_at = Column(DateTime, nullable=True, comment="Когда были собраны данные")
    source_url = Column(String(512), nullable=True, comment="Источник метрики")

    # Обратная связь
    metric = relationship("MetricModel", back_populates="periods", lazy="selectin", foreign_keys=[metric_id])
    data_entries = relationship(
        "MetricDataModel", back_populates="period", lazy="selectin", cascade="all, delete-orphan"
    )
