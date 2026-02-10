from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from src.core.database.models_and_mixins import AbstractBaseModel, CreatedUpdatedAtMixin


class MetricSeriesAttribute(AbstractBaseModel, CreatedUpdatedAtMixin):
    """Модель связи серий с атрибутами"""

    __tablename__ = "metric_series_attribute"

    __table_args__ = (
        UniqueConstraint("series_id", "attribute_type_id", "attribute_value_id", name="idx_series_attribute_unique"),
        Index("idx_series_attribute_type_value", "attribute_type_id", "attribute_value_id"),
        {
            "comment": "Связь серий данных с атрибутами/фильтрами - определяет, какие атрибуты применяются к каждой серии"
        },
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Уникальный идентификатор связи")

    series_id = Column(
        Integer,
        ForeignKey("metric_series_new.id", name="fk_series", ondelete="CASCADE"),
        nullable=False,
        comment="Ссылка на серию данных метрики",
    )

    attribute_type_id = Column(
        Integer,
        ForeignKey("metric_attribute_type.id", name="fk_attribute_type", ondelete="CASCADE"),
        nullable=False,
        comment="Ссылка на тип атрибута",
    )

    attribute_value_id = Column(
        Integer,
        ForeignKey("metric_attribute_value.id", name="fk_attribute_value", ondelete="CASCADE"),
        nullable=False,
        comment="Ссылка на значение атрибута",
    )

    is_filtered = Column(
        Boolean,
        nullable=True,
        comment="Используется ли атрибут для фильтрации (NULL - наследуется из типа, True/False - явное указание)",
    )

    is_primary = Column(
        Boolean, default=True, nullable=False, comment="Является ли это основным значением атрибута для серии"
    )

    sort_order = Column(
        Integer,
        default=0,
        nullable=True,
        comment="Порядок сортировки атрибутов (чем меньше значение, тем выше в списке)",
    )

    meta_data = Column(
        JSONB, default={}, nullable=False, comment="Метаданные связи в формате JSON (по умолчанию пустой объект)"
    )

    # Связи
    series = relationship("MetricSeriesNewModel", back_populates="series_attributes", overlaps="attributes")  # Добавить

    attribute_type = relationship("MetricAttributeTypeModel", back_populates="series_attributes")

    attribute_value = relationship(
        "MetricAttributeValueModel", back_populates="series_attributes", overlaps="series"  # Добавить
    )

    def __repr__(self):
        return (
            f"<MetricSeriesAttribute(id={self.id}, "
            f"series={self.series_id}, "
            f"type={self.attribute_type_id}, "
            f"value={self.attribute_value_id})>"
        )
