import logging

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from src.core.models.base_and_mixins import AbstractBaseModel, CreatedUpdatedAtMixin


logger = logging.getLogger(__name__)


class CityModel(AbstractBaseModel, CreatedUpdatedAtMixin):
    """Модель с данными о городе"""

    __tablename__ = "loc_city"

    __table_args__ = (
        # Уникальный индекс
        Index("uq_city_capital_per_country", "country_id", unique=True, postgresql_where=text("is_capital IS TRUE")),
        # Уникальное ограничение
        UniqueConstraint("country_id", "name", name="uq_city_country_name"),
        UniqueConstraint("country_id", "name_eng", name="uq_city_country_name_eng"),
        UniqueConstraint("latitude", "longitude", name="uq_city_coordinates"),
        #
        # Ограничение: latitude от -90 до 90, longitude от -180 до 180
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_city_latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_city_longitude_range"),
        #
        # Ограничение: в одной стране только один город со статусом is_capital = True
        CheckConstraint(
            """
            NOT is_capital OR
            (
                SELECT COUNT(*) FROM city c
                WHERE c.country_id = country_id AND c.is_capital = TRUE
            ) = 1
            """,
            name="ck_one_capital_per_country",
        ),
        # Partial unique index: одна столица на страну
        {"comment": "Города"},
    )

    # Идентификатор города
    id = Column(Integer, primary_key=True, index=True, comment="ID города")
    country_id = Column(
        Integer, ForeignKey("loc_country.id", ondelete="CASCADE"), nullable=False, index=True, comment="ID страны"
    )
    region_id = Column(
        Integer, ForeignKey("loc_region.id", ondelete="CASCADE"), nullable=True, index=True, comment="ID региона"
    )
    name = Column(String(255), nullable=False, index=True, comment="Название города")
    name_eng = Column(String(255), nullable=False, index=True, comment="Название города ENG")

    # Местоположение
    latitude = Column(Float, nullable=False, index=True, comment="Широта")
    longitude = Column(Float, nullable=False, index=True, comment="Долгота")

    # Характеристика города
    is_capital = Column(Boolean, nullable=False, default=False, server_default=text("false"), comment="Столица")
    timezone = Column(String(100), nullable=True, comment="Часовой пояс")
    population = Column(Integer, nullable=True, comment="Население города")
    language = Column(String(50), nullable=True, comment="Основной язык")
    climate = Column(String(100), nullable=True, comment="Климат")
    description = Column(Text, nullable=True, comment="Описание города")

    @hybrid_property
    def coordinates(self):
        """Координаты"""
        return f"{self.latitude},{self.longitude}"

    # Важные статусы
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"), comment="Отображение города")

    # Обратная связь
    country = relationship("CountryModel", back_populates="cities", lazy="noload", foreign_keys=[country_id])
    region = relationship("RegionModel", back_populates="cities", lazy="noload", foreign_keys=[region_id])
    metric_data = relationship("MetricDataModel", back_populates="city", lazy="noload", cascade="all, delete-orphan")
    images = relationship("ImageModel", back_populates="city", lazy="noload", cascade="all, delete-orphan")

    # ======== Классовые методы ========
