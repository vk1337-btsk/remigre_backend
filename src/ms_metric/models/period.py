from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from src.core.database.models_and_mixins import AbstractBaseModel, CreatedUpdatedAtMixin
from src.core.enums import PeriodTypeEnum


class MetricPeriodNewModel(AbstractBaseModel, CreatedUpdatedAtMixin):
    """Модель периодов данных метрик (новая структура)"""

    __tablename__ = "metric_period_new"

    __table_args__ = (
        CheckConstraint("date_start <= date_end", name="check_date_range"),
        CheckConstraint("period_month IS NULL OR (period_month >= 1 AND period_month <= 12)", name="check_month_range"),
        CheckConstraint(
            "period_quarter IS NULL OR (period_quarter >= 1 AND period_quarter <= 4)", name="check_quarter_range"
        ),
        CheckConstraint("period_week IS NULL OR (period_week >= 1 AND period_week <= 53)", name="check_week_range"),
        CheckConstraint("period_year >= 2000", name="check_year_range"),
        # Уникальность периода
        UniqueConstraint(
            "period_type", "period_year", "period_month", "period_quarter", "period_week", name="uq_period_components"
        ),
        # Индексы
        Index("idx_period_type", "period_type"),
        Index("idx_period_year", "period_year"),
        Index("idx_period_date", "date_start", "date_end"),
        Index("idx_period_active", "is_active", postgresql_where=text("is_active = true")),
        Index("idx_period_metadata", "meta_data", postgresql_using="gin"),
        Index("idx_period_components", "period_type", "period_year", "period_month", "period_quarter", "period_week"),
        {
            "comment": "Периоды данных метрик (обновленная схема) - содержит информацию о временных интервалах для данных метрик"
        },
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Уникальный идентификатор периода")

    period_type = Column(
        Enum(PeriodTypeEnum, name="period_type_enum", schema="public"), nullable=False, comment="Тип периода"
    )

    period_year = Column(Integer, nullable=False, comment="Год периода (обязательное поле, должен быть >= 2000)")
    period_month = Column(Integer, nullable=True, comment="Месяц периода (1-12, NULL если не применимо)")
    period_quarter = Column(Integer, nullable=True, comment="Квартал периода (1-4, NULL если не применимо)")
    period_week = Column(Integer, nullable=True, comment="Неделя периода (1-53, NULL если не применимо)")
    date_start = Column(Date, nullable=True, comment="Дата начала периода")
    date_end = Column(Date, nullable=True, comment="Дата окончания периода")

    collected_at = Column(DateTime, nullable=True, comment="Дата и время сбора данных для этого периода")

    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Активен ли период (true - используется, false - не используется)",
    )

    meta_data = Column(JSONB, nullable=True, comment="Метаданные периода в формате JSON (источник, метод сбора и т.д.)")

    # Связи
    data_entries = relationship("MetricDataNewModel", back_populates="period", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MetricPeriodNewModel(id={self.id},  year={self.period_year})>"
