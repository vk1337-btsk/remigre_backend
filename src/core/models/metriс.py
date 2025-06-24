from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from src.core.enum import PeriodTypeEnum, TypeCategoryEnum, TypeDataEnum
from src.core.models.base_models import AbstractBaseModel


class MetricCategoryModel(AbstractBaseModel):

    __tablename__ = "metric_category"

    __table_args__ = {"comment": "Информация об используемых метриках"}

    id = Column(Integer, primary_key=True, index=True, comment="ID метрики")

    short_name = Column(String(255), nullable=False, index=True, unique=True, comment="Краткое название метрики")
    full_name = Column(String(255), nullable=False, comment="Полное название метрики")

    description = Column(Text, nullable=False, comment="Описание метрики")

    source = Column(String(255), nullable=False, comment="Источник метрики")

    type_data = Column(Enum(TypeDataEnum), nullable=False, comment="Тип данных метрики (число/диапазон и т.д.)")
    type_category = Column(Enum(TypeCategoryEnum), nullable=False, comment="Объект метрики (город/страна/оба)")
    unit_format = Column(String(255), nullable=False, comment="Единица измерения метрики")

    # Обратная связь
    data = relationship(
        "MetricDataModel",
        back_populates="category",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    periods = relationship(
        "MetricPeriodModel",
        back_populates="category",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class MetricPeriodModel(AbstractBaseModel):

    __tablename__ = "metric_period"

    __table_args__ = {"comment": "Временной промежуток метрики (версия)"}

    id = Column(Integer, primary_key=True, index=True)

    # Связь с метрикой
    category_id = Column(
        Integer,
        ForeignKey("metric_category.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID категории метрики",
    )

    # Период
    period_type = Column(Enum(PeriodTypeEnum), nullable=False, comment="Тип периода метрики")
    period_year = Column(Integer, nullable=True, comment="Год (если указано)")
    period_month = Column(Integer, nullable=True, comment="Месяц (если указано)")

    # Интервал
    date_start = Column(DateTime, nullable=True, comment="Начало периода (для интервала)")
    date_end = Column(DateTime, nullable=True, comment="Конец периода (для интервала)")

    collected_at = Column(DateTime, nullable=True, comment="Когда были собраны данные")
    source_url = Column(String(512), nullable=True, comment="Источник метрики")

    # Обратная связь
    category = relationship(
        "MetricCategoryModel",
        back_populates="periods",
        lazy="selectin",
        foreign_keys=[category_id],
    )
    data_entries = relationship(
        "MetricDataModel",
        back_populates="period",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class MetricDataModel(AbstractBaseModel):
    """Модель, отражающая сырые данные."""

    __tablename__ = "metric_data"
    __table_args__ = {"comment": "Таблица с данными метрик"}

    id = Column(Integer, primary_key=True, index=True, comment="ID значения")

    # Связь с метриками
    category_id = Column(
        Integer,
        ForeignKey("metric_category.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID метрики",
    )
    period_id = Column(
        Integer,
        ForeignKey("metric_period.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID периода",
    )

    # Связь с локациями
    country_id = Column(
        Integer,
        ForeignKey("country.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID страны",
    )
    city_id = Column(
        Integer,
        ForeignKey("city.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="ID города",
    )

    value = Column(String(255), nullable=False, comment="Значение метрики")

    # Обратная связь
    category = relationship("MetricCategoryModel", back_populates="data", lazy="selectin", foreign_keys=[category_id])
    period = relationship("MetricPeriodModel", back_populates="data_entries", lazy="selectin", foreign_keys=[period_id])
    country = relationship("CountryModel", back_populates="data_entries", lazy="selectin", foreign_keys=[country_id])
    city = relationship("CityModel", back_populates="data_entries", lazy="selectin", foreign_keys=[city_id])
