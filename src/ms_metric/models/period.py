import logging
from typing import Any, Optional, Sequence

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    and_,
    func,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship, selectinload, with_loader_criteria

from src.core.database import AbstractBaseModel, CreatedUpdatedAtMixin, GetFilteredListDTO
from src.ms_metric.dto import (
    MetricPeriodCreateDTO,
    MetricPeriodGetDTO,
    MetricPeriodOptionsDTO,
    MetricPeriodUpdateDTO,
)
from src.ms_metric.enums import PeriodTypeEnum


logger = logging.getLogger(__name__)


class MetricPeriodModel(AbstractBaseModel, CreatedUpdatedAtMixin):
    """Модель периодов метрик"""

    __tablename__ = "metric_period"

    __table_args__ = (
        # Ограничение: год или не указан, или больше 2000
        CheckConstraint("(period_year IS NULL) OR (period_year >= 0)", name="ck_period_year_nonnegative"),
        # Ограничение: месяц или не указан, или между 1 и 12
        CheckConstraint("(period_month IS NULL) OR (period_month BETWEEN 1 AND 12)", name="ck_period_month_range"),
        # Ограничение: неделя или не указана, или между 1 и 55
        CheckConstraint("(period_week IS NULL) OR (period_week BETWEEN 1 AND 55)", name="ck_period_week_range"),
        # Ограничение: начало периода меньше конца периода
        CheckConstraint(
            "(date_start IS NULL OR date_end IS NULL) OR (date_start <= date_end)",
            name="ck_metric_period_date_start_lte_end",
        ),
        # Комментарий
        {"comment": "Периоды измерений метрики"},
    )

    # ID
    id = Column(Integer, primary_key=True, index=True, comment="ID периода")

    # Связи
    series_id = Column(
        Integer, ForeignKey("metric_series.id", ondelete="CASCADE"), nullable=False, index=True, comment="ID серии"
    )

    # Период
    period_type = Column(
        Enum(PeriodTypeEnum, name="period_type_enum"), nullable=False, index=True, comment="Тип периода метрики"
    )
    period_year = Column(Integer, nullable=True, index=True, comment="Год (если указано)")
    period_month = Column(Integer, nullable=True, index=True, comment="Месяц (если указано)")
    period_week = Column(Integer, nullable=True, index=True, comment="Неделя (если указано)")

    # Интервал
    date_start = Column(DateTime(timezone=True), nullable=True, comment="Начало периода (для интервала)")
    date_end = Column(DateTime(timezone=True), nullable=True, comment="Конец периода (для интервала)")

    # Дополнительно
    collected_at = Column(DateTime, nullable=True, comment="Когда были собраны данные")
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"), comment="Флаг активности")
    add_info = Column(JSONB, nullable=True, comment="Доп. информация")

    # ======== Обратная связь ========
    series = relationship("MetricSeriesModel", back_populates="periods", lazy="noload", foreign_keys=[series_id])
    data_entries = relationship("MetricDataModel", back_populates="period", lazy="noload", cascade="all, delete-orphan")

    @classmethod
    def _get_relationship_map(cls) -> dict[str, tuple[str, Any]]:
        """Возвращает отображение DTO-флагов на отношения модели"""

        return {
            "with_series": ("series", cls.series),
            "with_data": ("data_entries", cls.data_entries),
        }

    # ======== Классовые методы ========
    @classmethod
    async def get(
        cls,
        session: AsyncSession,
        dto_get: MetricPeriodGetDTO,
        dto_options: Optional[MetricPeriodOptionsDTO] = None,
        related_filters: Optional[dict[str, dict[str, Any]]] = None,
    ) -> Optional["MetricPeriodModel"]:
        """Возвращает объект MetricModel с опциональной подгрузкой связанных сущностей, если не найдено - None."""

        stmt = select(cls)

        # Определения условий поиска объекта
        # TODO: нужно расширить условия поиска
        if dto_get.id:
            stmt = stmt.where(cls.id == dto_get.id)
        else:
            raise ValueError(f"Не хватает данных для поиска метрики: {dto_get}")

        # Опциональная подгрузка связей
        stmt = stmt.options(*cls.__build_relationship_options(dto_options, related_filters))

        result = await session.execute(stmt.limit(1))

        logger.debug(f"Получение объекта {cls.__name__} - {result=} по данным: {dto_get=}.")

        return result.scalar_one_or_none()

    @classmethod
    async def create(cls, session: AsyncSession, dto_create: MetricPeriodCreateDTO) -> "MetricPeriodModel":
        """Создание нового объекта MetricPeriodModel."""

        instance = cls(**dto_create.model_dump(exclude_unset=True))
        session.add(instance)
        await session.commit()
        await session.refresh(instance)

        logger.debug(f"Создан объект {cls.__name__}: {instance}")

        return instance

    @classmethod
    async def get_or_create(cls, session: AsyncSession, dto_create: MetricPeriodCreateDTO) -> "MetricPeriodModel":
        """Получает существующий объект MetricPeriodModel или создаёт новый, если не найдена."""

        create_data = dto_create.model_dump(exclude_unset=True, exclude_none=True)
        stmt = select(cls)
        for field, value in create_data.items():
            if hasattr(cls, field):
                stmt = stmt.where(getattr(cls, field) == value)
        # JSONB-поля (add_info) нужно сравнивать отдельно
        if "add_info" in create_data and create_data["add_info"]:
            for key, val in create_data["add_info"].items():
                stmt = stmt.where(cls.add_info[key].astext == str(val))

        result = await session.execute(stmt.limit(1))
        instance = result.scalar_one_or_none()

        if instance:
            logger.debug(f"[MetricPeriodModel.get_or_create] Найден период: {instance.id}")
            return instance

        instance = cls(**create_data)
        session.add(instance)
        await session.commit()
        await session.refresh(instance)
        logger.debug(f"[MetricPeriodModel.get_or_create] Создан новый период: {instance.id}")
        return instance

    @classmethod
    async def update(
        cls,
        session: AsyncSession,
        dto_get: MetricPeriodGetDTO,
        dto_update: MetricPeriodUpdateDTO,
        dto_options: Optional[MetricPeriodOptionsDTO] = None,
    ) -> Optional["MetricPeriodModel"]:
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
    async def exists(cls, session: AsyncSession, dto_get: MetricPeriodGetDTO) -> bool:
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
        dto_options: Optional[MetricPeriodOptionsDTO] = None,
        related_filters: Optional[dict[str, dict[str, Any]]] = None,
    ) -> Sequence["MetricPeriodModel"]:
        """Получить список объектов MetricPeriodModel с возможностью:
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
    async def delete(cls, session: AsyncSession, dto_get: MetricPeriodGetDTO) -> bool:
        """Удаление объекта MetricPeriodModel. Возвращает True, если объект найден и удалён, иначе False."""

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
        dto_options: Optional[MetricPeriodOptionsDTO] = None,
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
