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

from src.core.database.models_and_mixins import AbstractBaseModel, CreatedUpdatedAtMixin


logger = logging.getLogger(__name__)


class RegionModel(AbstractBaseModel, CreatedUpdatedAtMixin):
    """Модель с данными о регионе"""

    __tablename__ = "loc_region"

    __table_args__ = (
        # Коммментарий
        {"comment": "Регионы"},
    )

    # Идентификатор региона/страны
    id = Column(Integer, primary_key=True, index=True, comment="ID региона")
    country_id = Column(
        Integer,
        ForeignKey("loc_country.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID страны",
    )
    name = Column(String(255), nullable=False, index=True, comment="Название региона")
    name_eng = Column(String(255), nullable=False, index=True, comment="Название региона ENG")

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
    country = relationship("CountryModel", back_populates="regions", lazy="noload", foreign_keys=[country_id])
    cities = relationship("CityModel", back_populates="region", lazy="noload", cascade="all, delete-orphan")

    # Классовые методы
