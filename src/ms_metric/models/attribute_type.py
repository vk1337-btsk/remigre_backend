from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Enum,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from src.core.database.models_and_mixins import AbstractBaseModel, CreatedUpdatedAtMixin
from src.core.enums import AttributeTypeValueEnum


class MetricAttributeTypeModel(AbstractBaseModel, CreatedUpdatedAtMixin):
    """Модель типа атрибута метрики"""

    __tablename__ = "metric_attribute_type"

    __table_args__ = (
        UniqueConstraint("code", name="metric_attribute_type_code_key"),
        CheckConstraint(
            "value_type IN ('string', 'number', 'currency', 'boolean')", name="metric_attribute_type_value_type_check"
        ),
        Index("idx_attribute_type_code", "code"),
        Index("idx_attribute_type_active", "is_active", postgresql_where=text("is_active = true")),
        Index("idx_attribute_type_is_filtered", "is_filtered"),
        Index("idx_attribute_type_metadata", "meta_data", postgresql_using="gin"),
        Index("idx_attribute_type_sort_order", "sort_order"),
        {
            "comment": "Типы атрибутов метрик - классификаторы для атрибутов (например, единицы измерения, источник данных и т.д.)"
        },
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Уникальный идентификатор типа атрибута")

    code = Column(String(255), nullable=False, comment="Уникальный код типа атрибута (например, 'unit', 'source')")
    name = Column(String(255), nullable=False, comment="Название типа атрибута")

    value_type = Column(
        Enum(AttributeTypeValueEnum, name="attribute_type_value_enum", schema="public"),
        nullable=False,
        comment="Тип значения атрибута (ENUM: string, currency)",
    )

    is_filtered = Column(Boolean, default=True, nullable=False, comment="Используется ли тип атрибута для фильтрации")
    is_active = Column(Boolean, default=True, nullable=False, comment="Активен ли тип атрибута")
    sort_order = Column(Integer, default=0, nullable=True, comment="Порядок сортировки типа атрибута")
    meta_data = Column(
        JSONB, default={}, nullable=False, comment="Дополнительные метаданные типа атрибута в формате JSON"
    )

    # Связи
    values = relationship(
        "MetricAttributeValueModel",
        back_populates="attribute_type",  # Это должно совпадать с именем в MetricAttributeValueModel
        cascade="all, delete-orphan",
        lazy="selectin",  # Добавьте для оптимизации
    )

    series_attributes = relationship("MetricSeriesAttribute", back_populates="attribute_type")

    def __repr__(self):
        return f"<MetricAttributeTypeModel(id={self.id}, code='{self.code}', name='{self.name}')>"
