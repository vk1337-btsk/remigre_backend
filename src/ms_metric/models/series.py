import logging
from typing import Any, Optional, Sequence

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    and_,
    cast,
    func,
    or_,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship, selectinload, with_loader_criteria

from src.core.database import AbstractBaseModel, CreatedUpdatedAtMixin, GetFilteredListDTO
from src.ms_metric.dto import (
    MetricSeriesCreateDTO,
    MetricSeriesGetDTO,
    MetricSeriesOptionsDTO,
    MetricSeriesUpdateDTO,
)


logger = logging.getLogger(__name__)


class MetricSeriesModel(AbstractBaseModel, CreatedUpdatedAtMixin):
    """Модель серии метрики"""

    __tablename__ = "metric_series"

    __table_args__ = (
        # Комментарий
        {"comment": "Серия измерений метрики"},
    )

    # ID
    id = Column(Integer, primary_key=True, index=True, comment="ID")

    # Связи
    metric_id = Column(
        Integer, ForeignKey("metric_info.id", ondelete="CASCADE"), nullable=False, index=True, comment="ID метрики"
    )

    # Дополнительные измерения / разрезы серий
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"), comment="Флаг активности")
    add_info = Column(JSONB, nullable=True, comment="Доп. информация")

    # ======== Вычисляемые значения ========
    @property
    def gender(self) -> Optional[str]:
        """Возвращает гендер, если есть."""

        return (self.add_info or {}).get("gender")

    # ======== Обратная связь ========
    metric = relationship("MetricInfoModel", back_populates="series", lazy="noload", foreign_keys=[metric_id])
    periods = relationship("MetricPeriodModel", back_populates="series", lazy="noload", cascade="all, delete-orphan")
    data_entries = relationship("MetricDataModel", back_populates="series", lazy="noload", cascade="all, delete-orphan")

    @classmethod
    def _get_relationship_map(cls) -> dict[str, tuple[str, Any]]:
        """Возвращает отображение DTO-флагов на отношения модели"""

        return {
            "with_metric": ("metric", cls.metric),
            "with_periods": ("periods", cls.periods),
            "with_data": ("data_entries", cls.data_entries),
        }

    # ======== Классовые методы ========
    @classmethod
    async def get(
        cls,
        session: AsyncSession,
        dto_get: MetricSeriesGetDTO,
        dto_options: Optional[MetricSeriesOptionsDTO] = None,
        related_filters: Optional[dict[str, dict[str, Any]]] = None,
    ) -> Optional["MetricSeriesModel"]:
        """Возвращает объект MetricModel с опциональной подгрузкой связанных сущностей, если не найдено - None."""

        stmt = select(cls)

        # Определения условий поиска объекта
        if dto_get.id:
            stmt = stmt.where(cls.id == dto_get.id)
        elif dto_get.metric_id is not None:
            stmt = stmt.where(cls.metric_id == dto_get.metric_id)
        else:
            raise ValueError(f"Не хватает данных для поиска : {dto_get}")

        # Опциональная подгрузка связей
        stmt = stmt.options(*cls.__build_relationship_options(dto_options, related_filters))

        result = await session.execute(stmt.limit(1))

        logger.debug(f"Получение объекта {cls.__name__} - {result=} по данным: {dto_get=}.")

        return result.scalar_one_or_none()

    @classmethod
    async def create(cls, session: AsyncSession, dto_create: MetricSeriesCreateDTO) -> "MetricSeriesModel":
        """Создание нового объекта MetricModel."""

        instance = cls(**dto_create.model_dump(exclude_unset=True))
        session.add(instance)

        await session.commit()
        await session.refresh(instance)

        logger.debug(f"Создан объект {cls.__name__}: {instance}")

        return instance

    @classmethod
    async def get_or_create(cls, session: AsyncSession, dto_create: MetricSeriesCreateDTO) -> "MetricSeriesModel":
        """Получает существующий объект MetricModel или создаёт новый, если не найден.
        Учитывает совпадение всех полей, включая точное совпадение JSONB add_info (все ключи и значения).
        """

        create_data = dto_create.model_dump(exclude_unset=True, exclude_none=True)
        if not create_data:
            raise ValueError(f"{cls.__name__}.get_or_create: DTO пустой, нечего сравнивать.")

        stmt = select(cls)

        # 1️⃣ Сравнение обычных полей
        for field, value in create_data.items():
            if field == "add_info":
                continue
            if hasattr(cls, field):
                stmt = stmt.where(getattr(cls, field) == value)

        # 2️⃣ Сравнение JSONB по ключам и значениям
        add_info_value = create_data.get("add_info")
        if add_info_value is None or add_info_value == {}:
            # Ищем записи без add_info или с пустым JSON
            stmt = stmt.where(or_(cls.add_info.is_(None), cls.add_info == cast({}, JSONB)))
        else:
            # Точное совпадение JSONB (оба содержат одинаковые ключи и значения)
            stmt = stmt.where(
                and_(
                    cls.add_info.op("@>")(cast(add_info_value, JSONB)),
                    cls.add_info.op("<@")(cast(add_info_value, JSONB)),
                )
            )

        # 3️⃣ Проверяем, есть ли такой объект
        result = await session.execute(stmt.limit(1))
        instance = result.scalar_one_or_none()

        if instance:
            logger.debug(f"[{cls.__name__}.get_or_create] Найден существующий объект: {instance}")
            return instance

        # 4️⃣ Если не найден — создаём новый
        instance = cls(**create_data)
        session.add(instance)
        await session.commit()
        await session.refresh(instance)

        logger.debug(f"[{cls.__name__}.get_or_create] Создан новый объект: {instance}")
        return instance

    @classmethod
    async def update(
        cls,
        session: AsyncSession,
        dto_get: MetricSeriesGetDTO,
        dto_update: MetricSeriesUpdateDTO,
        dto_options: Optional[MetricSeriesOptionsDTO] = None,
    ) -> Optional["MetricSeriesModel"]:
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
    async def exists(cls, session: AsyncSession, dto_get: MetricSeriesGetDTO) -> bool:
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
        dto_options: Optional[MetricSeriesOptionsDTO] = None,
        related_filters: Optional[dict[str, dict[str, Any]]] = None,
    ) -> Sequence["MetricSeriesModel"]:
        """Получить список объектов MetricModel с возможностью:
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
    async def delete(cls, session: AsyncSession, dto_get: MetricSeriesGetDTO) -> bool:
        """Удаление объекта MetricModel. Возвращает True, если объект найден и удалён, иначе False."""

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
        dto_options: Optional[MetricSeriesOptionsDTO] = None,
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
