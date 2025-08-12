import logging

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship

from src.core.database.base_models import AbstractBaseModel


logger = logging.getLogger(__name__)


class RegionModel(AbstractBaseModel):
    """Модель с данными о регионе"""

    __tablename__ = "region"

    __table_args__ = (
        UniqueConstraint("country_id", "name", name="uq_region_country_name"),
        UniqueConstraint("country_id", "name_eng", name="uq_region_country_name_eng"),
        {"comment": "Таблица регионов"},
    )

    # Идентификатор региона/страны
    id = Column(Integer, primary_key=True, index=True, comment="ID региона")
    country_id = Column(
        Integer,
        ForeignKey("country.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID страны",
    )
    name = Column(String(255), nullable=False, index=True, unique=True, comment="Название региона")
    name_eng = Column(String(255), nullable=False, index=True, unique=True, comment="Название региона ENG")

    # Характеристика региона
    description = Column(Text, nullable=True, comment="Описание региона")
    language = Column(String(50), nullable=True, comment="Основной язык региона")
    timezone = Column(String(50), nullable=True, comment="Часовой пояс региона")
    population = Column(Integer, nullable=True, comment="Население региона")
    climate = Column(String(100), nullable=True, comment="Климат региона")

    # Важные статусы
    is_active = Column(
        Boolean, nullable=False, default=True, server_default=text("true"), comment="Отображение региона"
    )

    # Обратная связь
    country = relationship("CountryModel", back_populates="regions", lazy="selectin", foreign_keys=[country_id])
    cities = relationship("CityModel", back_populates="region", lazy="selectin", cascade="all, delete-orphan")

    # Классовые методы
