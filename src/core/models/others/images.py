from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    text,
)
from sqlalchemy.orm import relationship

from src.core.models.base_and_mixins import AbstractBaseModel, CreatedUpdatedAtMixin


class ImageModel(AbstractBaseModel, CreatedUpdatedAtMixin):
    """Модель для хранения изображений"""

    __tablename__ = "data_images"
    __table_args__ = (
        CheckConstraint(
            "(city_id IS NOT NULL AND country_id IS NULL) OR (city_id IS NULL AND country_id IS NOT NULL)",
            name="check_city_or_country",
        ),
        # Комментарий к таблице
        {"comment": "Изоображения"},
    )

    id = Column(Integer, primary_key=True, comment="ID изображения")
    country_id = Column(Integer, ForeignKey("loc_country.id", ondelete="CASCADE"), nullable=True, comment="ID страны")
    city_id = Column(Integer, ForeignKey("loc_city.id", ondelete="CASCADE"), nullable=True, comment="ID города")
    file_data = Column(LargeBinary, nullable=False, comment="Бинарные данные изображения")
    file_path = Column(String(500), nullable=False, comment="Путь к файлу")
    file_name = Column(String(255), nullable=False, comment="Название файла")
    mime_type = Column(String(100), comment="MIME тип")
    is_main = Column(Boolean, default=False, nullable=False, comment="Статус главной картинки")
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"), comment="Статус отображения")
    caption = Column(Text, comment="Название картинки")
    sort_order = Column(Integer, default=0, nullable=False, comment="Сортировка")

    # Обратная связь
    city = relationship("CityModel", back_populates="images")
    country = relationship("CountryModel", back_populates="images")
