from sqlalchemy import (
    Boolean,
    Column,
    Enum,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from src.core.database.models_and_mixins import AbstractBaseModel, CreatedUpdatedAtMixin
from src.core.enums import CategoryMetricEnum, TypeDataEnum


class MetricInfoNewModel(AbstractBaseModel, CreatedUpdatedAtMixin):
    """Модель метрики (новая структура)"""

    __tablename__ = "metric_info_new"

    __table_args__ = (
        UniqueConstraint("slug", name="metric_info_new_slug_key"),
        Index("idx_metric_info_slug", "slug"),
        Index("idx_metric_info_category", "category"),
        Index("idx_metric_info_country_list", "id", postgresql_where=text("show_in_country_list = true")),
        Index("idx_metric_info_primary", "id", postgresql_where=text("is_primary = true")),
        {"comment": "Таблица метрик (обновленная схема) - содержит основную информацию о метриках и показателях"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Уникальный идентификатор метрики")
    slug = Column(String(255), nullable=False, comment="Уникальный идентификатор метрики в URL (человеко-читаемый)")
    name = Column(String(255), nullable=False, comment="Название метрики")
    description = Column(Text, nullable=True, comment="Подробное описание метрики")
    category = Column(
        Enum(CategoryMetricEnum, name="category_metric_enum", schema="public"),
        nullable=False,
        comment="Категория метрики (ENUM: ECONOMY, SECURITY, QUALITY_OF_LIFE, EMIGRATION, UNCATEGORIZED)",
    )
    source_name = Column(String(255), nullable=True, comment="Название источника данных")
    source_url = Column(String(512), nullable=True, comment="URL источника данных")
    data_type = Column(
        Enum(TypeDataEnum, name="type_data_enum", schema="public"),
        nullable=False,
        comment="Тип данных метрики (ENUM: STRING, FLOAT, RANGE, BOOL)",
    )

    # Параметры отображения
    show_in_country_list = Column(Boolean, default=False, nullable=True, comment="Показывать метрику в списке стран")
    show_in_city_list = Column(Boolean, default=False, nullable=True, comment="Показывать метрику в списке городов")
    show_in_country_detail = Column(
        Boolean, default=False, nullable=True, comment="Показывать метрику в детальной странице страны"
    )
    show_in_city_detail = Column(
        Boolean, default=False, nullable=True, comment="Показывать метрику в детальной странице города"
    )
    list_priority = Column(
        Integer,
        default=0,
        nullable=True,
        comment="Приоритет отображения в списках (чем выше значение, тем выше в списке)",
    )
    detail_priority = Column(Integer, default=0, nullable=True, comment="Приоритет отображения в детальных страницах")
    is_primary = Column(
        Boolean, default=False, nullable=True, comment="Является ли метрика основной (ключевые показатели)"
    )
    is_secondary = Column(Boolean, default=False, nullable=True, comment="Является ли метрика вспомогательной")

    # Дополнительные поля
    meta_data = Column(
        JSONB,
        nullable=True,
        comment="Метаданные в формате JSON (NULL - нет данных, JSON - есть данные)",
    )
    is_active = Column(
        Boolean, default=True, nullable=True, comment="Активна ли метрика (true - отображается, false - скрыта)"
    )

    # Связи
    series = relationship("MetricSeriesNewModel", back_populates="metric", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MetricInfoNewModel(id={self.id}, name='{self.name}', slug='{self.slug}')>"
