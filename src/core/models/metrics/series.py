from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from src.core.models.base_and_mixins import AbstractBaseModel, CreatedUpdatedAtMixin


class MetricSeriesModel(AbstractBaseModel, CreatedUpdatedAtMixin):

    __tablename__ = "metric_series"

    __table_args__ = (
        # Уникальный индекс (ограничение) для комбинации metric_id и attributes_hash,
        # действует только когда attributes_hash не NULL
        Index(
            "idx_series_hash_unique",
            "metric_id",
            "attributes_hash",
            unique=True,
            postgresql_where=text("attributes_hash IS NOT NULL"),
        ),
        # Составной индекс для фильтрации по метрике и активности
        Index("idx_metric_series_metric_active", "metric_id", "is_active"),
        # Частичный индекс для быстрого доступа к активным сериям
        Index("idx_series_active", "id", postgresql_where=text("is_active = true")),
        # Индекс для поиска серий по метрике (без учёта активности)
        Index("idx_series_metric", "metric_id"),
        # Комментарий к таблице
        {
            "comment": "Серии данных метрик (обновленная схема) - содержит различные варианты/серии одной метрики с разными атрибутами"
        },
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Уникальный идентификатор серии")
    metric_id = Column(
        Integer,
        ForeignKey("metric_info.id", name="metric_series_new_metric_id_fkey"),
        nullable=True,
        comment="Ссылка на метрику (внешний ключ к metric_info_new)",
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=True,
        comment="Активна ли серия (true - данные собираются, false - сбор остановлен)",
    )
    is_preset = Column(
        Boolean,
        default=False,
        nullable=True,
        comment="Является ли серия предустановленной (системной) или создана пользователем",
    )
    attributes_hash = Column(
        String(255),
        nullable=True,
        index=True,
        comment="Хэш от отсортированного списка пар (attribute_type_id, attribute_value_id)",
    )
    meta_data = Column(
        JSONB, nullable=True, default=None, comment="Метаданные в формате JSON (NULL - нет данных, JSON - есть данные)"
    )

    # Связи
    metric = relationship("MetricInfoModel", back_populates="series")

    attributes = relationship(
        "MetricAttributeValueModel",
        secondary="metric_series_attribute",
        back_populates="series",
        viewonly=True,
        overlaps="series_attributes",
    )

    data = relationship(
        "MetricDataModel",
        back_populates="series",
        cascade="all, delete-orphan",
        foreign_keys="[MetricDataModel.series_id]",
    )

    series_attributes = relationship(
        "MetricSeriesAttribute", back_populates="series", cascade="all, delete-orphan", overlaps="attributes"
    )
    presets = relationship("MetricPresetModel", back_populates="series", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MetricSeriesModel(id={self.id}, metric_id={self.metric_id})>"
