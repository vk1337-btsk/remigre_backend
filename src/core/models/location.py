from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from src.core.models.base_models import AbstractBaseModel


class CountryModel(AbstractBaseModel):

    __tablename__ = "country"

    __table_args__ = {"comment": "Таблица стран и данными о них"}

    id = Column(Integer, primary_key=True, index=True, comment="ID страны")
    name = Column(String(255), nullable=False, index=True, unique=True, comment="Название страны")
    name_eng = Column(String(255), nullable=False, index=True, unique=True, comment="Название страны ENG")
    iso_code = Column(String(10), nullable=False, index=True, unique=True, comment="Код страны ISO 3166")

    # Характеристика страны
    language = Column(String(50))
    currency = Column(String(10))
    timezone = Column(String(50))
    migration_policy = Column(String)  # краткое описание
    description = Column(String)  # опционально
    population = Column(Integer)
    climate = Column(String(100))

    # Обратная связь
    cities = relationship("CityModel", back_populates="country", lazy="selectin", cascade="all, delete-orphan")
    data_entries = relationship(
        "MetricDataModel", back_populates="country", lazy="selectin", cascade="all, delete-orphan"
    )


class CityModel(AbstractBaseModel):

    __tablename__ = "city"

    __table_args__ = (
        UniqueConstraint("latitude", "longitude", name="uq_city_coordinates"),
        {"comment": "Таблица городов и данными о них"},
    )

    id = Column(Integer, primary_key=True, index=True, comment="ID города")
    country_id = Column(
        Integer, ForeignKey("country.id", ondelete="CASCADE"), nullable=False, index=True, comment="ID страны"
    )

    name = Column(String(255), nullable=False, index=True, comment="Название города")
    name_eng = Column(String(255), nullable=False, index=True, comment="Название города ENG")

    latitude = Column(Float, nullable=False, index=True, comment="Широта")
    longitude = Column(Float, nullable=False, index=True, comment="Долгота")

    # Характеристика города
    is_capital = Column(Boolean, nullable=False, comment="Столица")
    timezone = Column(String(100), nullable=True, comment="Часовой пояс")
    region = Column(String(255), nullable=True, comment="Регион")

    population = Column(Integer)
    language = Column(String(50))
    climate = Column(String(100))
    description = Column(String)

    # Обратная связь
    country = relationship("CountryModel", back_populates="cities", lazy="selectin", foreign_keys=[country_id])
    data_entries = relationship("MetricDataModel", back_populates="city", lazy="selectin", cascade="all, delete-orphan")

    @hybrid_property
    def coordinates(self):
        return f"{self.latitude},{self.longitude}"
