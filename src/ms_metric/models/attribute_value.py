from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from src.core.database.models_and_mixins import AbstractBaseModel, CreatedUpdatedAtMixin


class MetricAttributeValueModel(AbstractBaseModel, CreatedUpdatedAtMixin):
    """Модель значения атрибута метрики"""

    __tablename__ = "metric_attribute_value"

    __table_args__ = (
        UniqueConstraint("attribute_type_id", "code", name="metric_attribute_value_attribute_type_id_code_key"),
        Index("idx_attribute_value_code", "code"),
        Index("idx_attribute_value_type", "attribute_type_id"),
        Index("idx_attribute_value_active", "is_active", postgresql_where=text("is_active = true")),
        Index("idx_attribute_value_metadata", "meta_data", postgresql_using="gin"),
        Index("idx_attribute_value_sort", "attribute_type_id", "sort_order"),
        {
            "comment": "Значения атрибутов метрик - конкретные значения для каждого типа атрибута (например, 'USD', 'Евро' для типа 'единица_измерения')"
        },
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Уникальный идентификатор значения атрибута")

    attribute_type_id = Column(
        Integer,
        ForeignKey("metric_attribute_type.id", name="fk_attribute_value_type", ondelete="CASCADE"),
        nullable=False,
        comment="Ссылка на тип атрибута",
    )

    code = Column(String(255), nullable=False, comment="Код значения атрибута (уникальный в пределах типа атрибута)")
    name = Column(String(255), nullable=False, comment="Название значения атрибута")
    is_active = Column(Boolean, default=True, nullable=False, comment="Активно ли значение атрибута")
    is_filtered = Column(Boolean, default=True, nullable=False, comment="Используется ли тип атрибута для фильтрации")
    sort_order = Column(Integer, default=0, nullable=True, comment="Порядок сортировки значения атрибута")
    meta_data = Column(
        JSONB, default={}, nullable=False, comment="Дополнительные метаданные значения атрибута в формате JSON"
    )

    # Связи (ДОБАВЬТЕ attribute_type!)
    attribute_type = relationship(
        "MetricAttributeTypeModel",
        back_populates="values",  # Это должно совпадать с именем в MetricAttributeTypeModel
        foreign_keys=[attribute_type_id],
    )

    # Две связи для compatibility
    series = relationship(
        "MetricSeriesNewModel",
        secondary="metric_series_attribute",
        back_populates="attributes",
        viewonly=True,
        overlaps="series_attributes,series",
    )

    series_attributes = relationship("MetricSeriesAttribute", back_populates="attribute_value", overlaps="series")

    def __repr__(self):
        return f"<MetricAttributeValueModel(id={self.id}, code='{self.code}', name='{self.name}')>"
