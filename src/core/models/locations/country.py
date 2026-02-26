import logging

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Float,
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


class CountryModel(AbstractBaseModel, CreatedUpdatedAtMixin):
    """Модель с данными о стране"""

    __tablename__ = "loc_country"
    __table_args__ = (
        # Уникальные ограничения
        UniqueConstraint("latitude", "longitude", name="uq_loc_country_coordinates"),
        UniqueConstraint("iso_alpha_2", name="uq_loc_country_iso_alpha_2"),
        UniqueConstraint("iso_alpha_3", name="uq_loc_country_iso_alpha_3"),
        UniqueConstraint("iso_digits", name="uq_loc_country_iso_digits"),
        UniqueConstraint("name", name="uq_loc_country_name"),
        UniqueConstraint("name_eng", name="uq_loc_country_name_eng"),
        # Проверки
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_loc_country_latitude_range"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_loc_country_longitude_range"),
        # Индексы
        Index("idx_loc_country_active_name", "is_active", "name"),
        Index("idx_loc_country_geometry", "geometry", postgresql_using="gist"),
        Index("idx_loc_country_is_active", "is_active"),
        Index("idx_loc_country_iso_alpha_2", "iso_alpha_2"),
        Index("idx_loc_country_iso_alpha_3", "iso_alpha_3"),
        Index("idx_loc_country_iso_digits", "iso_digits"),
        Index("idx_loc_country_latitude", "latitude"),
        Index("idx_loc_country_longitude", "longitude"),
        Index("idx_loc_country_lower_name", text("lower(name)")),
        Index("idx_loc_country_lower_name_eng", text("lower(name_eng)")),
        Index("idx_loc_country_name", "name"),
        Index("idx_loc_country_name_eng", "name_eng"),
        # Комментарий к таблице
        {"comment": "Таблица стран и данными о них"},
    )

    # Идентификаторы страны
    id = Column(Integer, primary_key=True, comment="ID страны")
    name = Column(String(255), nullable=False, comment="Название")
    name_eng = Column(String(255), nullable=False, comment="Название (ENG)")

    # Код страны
    iso_alpha_2 = Column(String(2), nullable=False, comment="Код ISO (2-х символьный)")
    iso_alpha_3 = Column(String(3), nullable=False, comment="Код ISO (3-х символьный)")
    iso_digits = Column(String(3), nullable=True, comment="Код ISO (числовой)")

    # Местоположение
    latitude = Column(Float, nullable=False, comment="Широта")
    longitude = Column(Float, nullable=False, comment="Долгота")
    geometry = Column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=True, comment="Геометрия страны (GeoJSON)"
    )

    # Характеристика страны
    language = Column(String(50), nullable=True, comment="Язык")
    currency = Column(String(10), nullable=True, comment="Валюта")
    timezone = Column(String(50), nullable=True, comment="Часовой пояс")
    migration_policy = Column(Text, nullable=True, comment="Краткое описание миграционной политики")
    description = Column(Text, nullable=True, comment="Описание")
    population = Column(Integer, nullable=True, comment="Население")
    climate = Column(String(100), nullable=True, comment="Климат")

    # Важные статусы
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"), comment="Статус отображения")

    # Обратная связь
    regions = relationship("RegionModel", back_populates="country", lazy="noload", cascade="all, delete-orphan")
    cities = relationship("CityModel", back_populates="country", lazy="noload", cascade="all, delete-orphan")
    metric_data = relationship("MetricDataModel", back_populates="country", lazy="noload", cascade="all, delete-orphan")

    @hybrid_property
    def coordinates(self):
        """Координаты"""
        return f"{self.latitude},{self.longitude}"

    def __repr__(self):
        return f"<CountryModel id={self.id} name={self.name} iso_code={self.iso_alpha_2}>"
