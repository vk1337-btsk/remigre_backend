import logging
from typing import Any, Optional, Sequence

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    and_,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship, selectinload, with_loader_criteria

from src.core.database import (
    AbstractBaseModel,
    CreatedUpdatedAtMixin,
    GetFilteredListDTO,
)
from src.ms_metric.dto import (
    MetricDataCreateDTO,
    MetricDataGetDTO,
    MetricDataOptionsDTO,
    MetricDataUpdateDTO,
)


logger = logging.getLogger(__name__)


class MetricDataModel(AbstractBaseModel, CreatedUpdatedAtMixin):
    """Модель, отражающая сырые данные метрик."""

    __tablename__ = "metric_data"

    __table_args__ = (
        # Уникальное ограничение по данным метрики + локации
        UniqueConstraint("series_id", "period_id", "country_id", "city_id", name="uq_metric_data_entries"),
        # Ограничение: страна или говрод задан
        CheckConstraint(
            "(city_id IS NOT NULL) OR (country_id IS NOT NULL)", name="ck_metric_data_city_or_country_not_null"
        ),
        # Ограничение: в диапазоне range_max больше range_min
        CheckConstraint(
            "(value_range_min IS NULL OR value_range_max IS NULL) OR (value_range_min <= value_range_max)",
            name="ck_metric_data_range_min_lte_max",
        ),
        # Ограничение: заполнен ровно один тип значения из всех возможных
        CheckConstraint(
            """
            (
                (CASE WHEN value_int IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN value_float IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN value_range_min IS NOT NULL OR value_range_max IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN value_bool IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN value_string IS NOT NULL THEN 1 ELSE 0 END)
            ) = 1
            """,
            name="ck_metric_data_only_one_value_filled",
        ),
        # Комментарий
        {"comment": "Данные метрики"},
    )

    # ID
    id = Column(Integer, primary_key=True, index=True, comment="ID значения")

    # Связи
    series_id = Column(
        Integer, ForeignKey("metric_series.id", ondelete="CASCADE"), nullable=False, index=True, comment="ID серии"
    )
    period_id = Column(
        Integer, ForeignKey("metric_period.id", ondelete="CASCADE"), nullable=False, index=True, comment="ID периода"
    )
    country_id = Column(
        Integer, ForeignKey("loc_country.id", ondelete="CASCADE"), nullable=True, index=True, comment="ID страны"
    )
    city_id = Column(
        Integer, ForeignKey("loc_city.id", ondelete="CASCADE"), nullable=True, index=True, comment="ID города"
    )

    # Значение метрики
    value_int = Column(Integer, nullable=True, index=True, comment="Значение в формате INT/NUMERIC")
    value_string = Column(String(255), nullable=True, comment="Значение в формате STRING")
    value_float = Column(Float, nullable=True, index=True, comment="Значение в формате FLOAT")
    value_range_min = Column(Float, nullable=True, index=True, comment="Значение в формате MIN RANGE")
    value_range_max = Column(Float, nullable=True, index=True, comment="Значение в формате MAX RANGE")
    value_bool = Column(Boolean, nullable=True, comment="Значение в формате BOOL")

    # Дополнительно
    add_info = Column(JSONB, nullable=True, comment="Дополнительная информация")

    # ======== Обратная связь ========
    series = relationship("MetricSeriesModel", back_populates="data_entries", lazy="noload", foreign_keys=[series_id])
    period = relationship("MetricPeriodModel", back_populates="data_entries", lazy="noload", foreign_keys=[period_id])
    country = relationship("CountryModel", back_populates="data_entries", lazy="noload", foreign_keys=[country_id])
    city = relationship("CityModel", back_populates="data_entries", lazy="noload", foreign_keys=[city_id])

    @classmethod
    def _get_relationship_map(cls) -> dict[str, tuple[str, Any]]:
        """Возвращает отображение DTO-флагов на отношения модели"""

        return {
            "with_series": ("series", cls.series),
            "with_period": ("period", cls.period),
            "with_country": ("country", cls.country),
            "with_city": ("city", cls.city),
        }

    # ======== Классовые методы ========
    @classmethod
    async def get(
        cls,
        session: AsyncSession,
        dto_get: MetricDataGetDTO,
        dto_options: Optional[MetricDataOptionsDTO] = None,
        related_filters: Optional[dict[str, dict[str, Any]]] = None,
    ) -> Optional["MetricDataModel"]:
        """Возвращает объект MetricModel с опциональной подгрузкой связанных сущностей, если не найдено - None."""

        stmt = select(cls)

        # Определения условий поиска объекта
        # TODO: нужно расширить условия поиска
        if dto_get.id:
            stmt = stmt.where(cls.id == dto_get.id)
        else:
            ValueError(f"Не хватает данных для поиска метрики: {dto_get}")

        # Опциональная подгрузка связей
        stmt = stmt.options(*cls.__build_relationship_options(dto_options, related_filters))

        result = await session.execute(stmt.limit(1))

        logger.debug(f"Получение объекта {cls.__name__} - {result=} по данным: {dto_get=}.")

        return result.scalar_one_or_none()

    @classmethod
    async def create(cls, session: AsyncSession, dto_create: MetricDataCreateDTO) -> "MetricDataModel":
        """Создание нового объекта MetricDataModel."""

        instance = cls(**dto_create.model_dump(exclude_unset=True))
        session.add(instance)
        await session.commit()
        await session.refresh(instance)

        logger.debug(f"Создан объект {cls.__name__}: {instance}")

        return instance

    @classmethod
    async def get_or_create(cls, session: AsyncSession, dto_create: MetricDataCreateDTO) -> "MetricDataModel":
        """Получает существующий объект MetricDataModel или создаёт новый, если не найдена."""

        create_data = dto_create.model_dump(exclude_unset=True, exclude_none=True)
        stmt = select(cls)
        for field, value in create_data.items():
            if hasattr(cls, field):
                stmt = stmt.where(getattr(cls, field) == value)
        if "add_info" in create_data and create_data["add_info"]:
            for key, val in create_data["add_info"].items():
                stmt = stmt.where(cls.add_info[key].astext == str(val))

        result = await session.execute(stmt.limit(1))
        instance = result.scalar_one_or_none()

        if instance:
            logger.debug(f"[MetricDataModel.get_or_create] Найдено значение: {instance.id}")
            return instance

        instance = cls(**create_data)
        session.add(instance)
        await session.commit()
        await session.refresh(instance)
        logger.debug(f"[MetricDataModel.get_or_create] Создано новое значение: {instance.id}")
        return instance

    @classmethod
    async def update(
        cls,
        session: AsyncSession,
        dto_get: MetricDataGetDTO,
        dto_update: MetricDataUpdateDTO,
        dto_options: Optional[MetricDataOptionsDTO] = None,
    ) -> Optional["MetricDataModel"]:
        """Обновление существующего объекта, если не найдено - None."""

        instance = await cls.get(session, dto_get, dto_options)
        if not instance:
            logger.debug(f"Объект {cls.__name__} по данным {dto_get=} не найден для обновления.")
            return None

        update_data = dto_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(instance, key, value)

        session.add(instance)

        await session.commit()
        await session.refresh(instance)

        logger.debug(f"Объект {cls.__name__} обновлён по данным {dto_get=}: {update_data}")
        return instance

    @classmethod
    async def exists(cls, session: AsyncSession, dto_get: MetricDataGetDTO) -> bool:
        """Возвращает True, если объект существует, иначе False."""

        stmt = select(cls.id)

        # Определения условий поиска объекта
        filters = dto_get.model_dump(exclude_unset=True)
        for field, value in filters.items():
            column = getattr(cls, field, None)
            if column is not None:
                stmt = stmt.where(column == value)

        result = await session.execute(stmt.limit(1))

        logger.debug(f"Получение объекта {cls.__name__} - {result=} по данным: {dto_get=}.")

        return result.scalar_one_or_none() is not None

    @classmethod
    async def get_all_filtered(
        cls,
        session: AsyncSession,
        dto_filters: Optional[GetFilteredListDTO] = None,
        dto_options: Optional[MetricDataOptionsDTO] = None,
        related_filters: Optional[dict[str, dict[str, Any]]] = None,
    ) -> Sequence["MetricDataModel"]:
        """Получить список объектов MetricDataModel с возможностью:
        - фильтрации по точным, LIKE- и IN-условиям с поддержкой пагинации по dto_filters. Если не задан -
            вернёт все объекты
        - подгрузки связанных сущностей
        """

        stmt = select(cls)

        # Осуществляем фильтрацию
        if dto_filters:

            # Точное сравнение
            filters = dto_filters.filters or {}
            for key, value in filters.items():
                column = getattr(cls, key, None)
                if column is not None:
                    stmt = stmt.where(column == value)

            # LIKE-фильтрация
            like_filters = dto_filters.like_filters or {}
            for key, value in like_filters.items():
                column = getattr(cls, key, None)
                if column is not None:
                    stmt = stmt.where(func.lower(column).like(f"%{value.lower()}%"))

            # IN-фильтрация
            in_filters = dto_filters.in_filters or {}
            for key, values in in_filters.items():
                column = getattr(cls, key, None)
                if column is not None:
                    stmt = stmt.where(column.in_(values))

            # Пагинация
            if dto_filters.offset:
                stmt = stmt.offset(dto_filters.offset)
            if dto_filters.limit:
                stmt = stmt.limit(dto_filters.limit)

        stmt = stmt.order_by(getattr(cls, "id"))

        # Опциональная подгрузка связей
        stmt = stmt.options(*cls.__build_relationship_options(dto_options, related_filters))

        result = await session.execute(stmt)

        logger.debug(f"Выполнение запроса {cls.__name__} с фильтрами {dto_filters} и опциями {dto_options}")

        return result.scalars().all()

    @classmethod
    async def delete(cls, session: AsyncSession, dto_get: MetricDataGetDTO) -> bool:
        """Удаление объекта MetricDataModel. Возвращает True, если объект найден и удалён, иначе False."""

        instance = await cls.get(session, dto_get)
        if not instance:
            logger.debug(f"Объект {cls.__name__} с данными для поиска {dto_get=} не найден и не удалён.")
            return False

        await session.delete(instance)
        await session.commit()

        logger.debug(f"Объект {cls.__name__} с данными для поиска {dto_get=} найден и удалён.")

        return True

    # ======== Вспомогательные классовые методы ========
    @classmethod
    def __build_relationship_options(
        cls,
        dto_options: Optional[MetricDataOptionsDTO] = None,
        related_filters: Optional[dict[str, dict[str, Any]]] = None,
    ) -> list:
        """Формирует SQLAlchemy options() для подгрузки связей с фильтрацией."""

        def _build_filter_conditions(model_cls, filters: dict[str, Any]):
            conditions = []
            for field, value in filters.items():
                column = getattr(model_cls, field, None)
                if column is not None:
                    conditions.append(column == value)
            return and_(*conditions) if conditions else None

        if not dto_options:
            return []

        options = []
        relationship_map = cls._get_relationship_map()

        for dto_field, (relation_name, relation_attr) in relationship_map.items():
            # Добавляем опцию ТОЛЬКО если флаг в dto_options равен True
            if dto_options and getattr(dto_options, dto_field, False) is True:
                options.append(selectinload(relation_attr))
                # Фильтры для подгрузки
                if related_filters and relation_name in related_filters:
                    model_cls = relation_attr.property.mapper.class_
                    criteria = _build_filter_conditions(model_cls, related_filters[relation_name])
                    if criteria is not None:
                        options.append(with_loader_criteria(model_cls, criteria))

        return options
