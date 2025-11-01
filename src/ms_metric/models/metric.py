import logging
from typing import Any, Optional, Sequence

from sqlalchemy import (
    Boolean,
    Column,
    Enum,
    Integer,
    String,
    Text,
    and_,
    func,
    select,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship, selectinload, with_loader_criteria

from src.core.database import AbstractBaseModel, GetFilteredListDTO
from src.ms_metric.dto import (
    MetricCreateDTO,
    MetricGetDTO,
    MetricOptionsDTO,
    MetricUpdateDTO,
)
from src.ms_metric.enums import CategoryMetricEnum, TypeDataEnum


logger = logging.getLogger(__name__)


class MetricModel(AbstractBaseModel):
    """Модель категории метрики"""

    __tablename__ = "metric_info"

    __table_args__ = ({"comment": "Информация об используемых метриках"},)

    id = Column(Integer, primary_key=True, index=True, comment="ID метрики")

    # Название и описание метрики
    slug = Column(
        String(255), nullable=False, index=True, unique=True, comment="Slug метрики (нужен как текстовой идентификатор)"
    )
    name = Column(String(255), nullable=False, comment="Название метрики")
    description = Column(Text, nullable=True, comment="Описание метрики")
    category = Column(Enum(CategoryMetricEnum), nullable=False, comment="Категория метрики")

    # Характеристики метрики
    source_name = Column(String(255), nullable=True, comment="Название источника метрики")
    source_url = Column(String(255), nullable=True, comment="URL источника метрики")
    type_data = Column(Enum(TypeDataEnum), nullable=False, comment="Тип данных метрики (int/str/range/bool)")
    unit_format = Column(String(255), nullable=False, comment="Единица измерения метрики")

    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"), comment="Активность метрики")

    # Обратная связь
    data = relationship("MetricDataModel", back_populates="metric", lazy="selectin", cascade="all, delete-orphan")
    periods = relationship("MetricPeriodModel", back_populates="metric", lazy="selectin", cascade="all, delete-orphan")

    # ======== Классовые методы ========
    @classmethod
    def _get_relationship_map(cls) -> dict[str, tuple[str, Any]]:
        """Возвращает отображение DTO-флагов на отношения модели"""

        return {
            "with_data": ("regions", cls.data),
            "with_period": ("cities", cls.periods),
        }

    @classmethod
    async def create(cls, session: AsyncSession, dto_create: MetricCreateDTO) -> "MetricModel":
        """Создание нового объекта MetricModel."""

        instance = cls(**dto_create.model_dump(exclude_unset=True))
        session.add(instance)

        await session.commit()
        await session.refresh(instance)

        logger.debug(f"Создан объект {cls.__name__}: {instance}")

        return instance

    @classmethod
    async def update(
        cls,
        session: AsyncSession,
        dto_get: MetricGetDTO,
        dto_update: MetricUpdateDTO,
        dto_options: Optional[MetricOptionsDTO] = None,
    ) -> Optional["MetricModel"]:
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
    async def exists(cls, session: AsyncSession, dto_get: MetricGetDTO) -> bool:
        """Возвращает True, если объект существует, иначе False."""

        stmt = select(getattr(cls, "id"))

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
    async def get(
        cls,
        session: AsyncSession,
        dto_get: MetricGetDTO,
        dto_options: Optional[MetricOptionsDTO] = None,
        related_filters: Optional[dict[str, dict[str, Any]]] = None,
    ) -> Optional["MetricModel"]:
        """Возвращает объект MetricModel с опциональной подгрузкой связанных сущностей, если не найдено - None."""

        stmt = select(cls)

        # Определения условий поиска объекта
        if dto_get.id:
            stmt = stmt.where(cls.id == dto_get.id)
        elif dto_get.slug:
            stmt = stmt.where(cls.slug == dto_get.slug)
        else:
            ValueError(f"Не хватает данных для поиска метрики: {dto_get}")

        # Опциональная подгрузка связей
        stmt = stmt.options(*cls.__build_relationship_options(dto_options, related_filters))

        result = await session.execute(stmt.limit(1))

        logger.debug(f"Получение объекта {cls.__name__} - {result=} по данным: {dto_get=}.")

        return result.scalar_one_or_none()

    @classmethod
    async def get_all_filtered(
        cls,
        session: AsyncSession,
        dto_filters: Optional[GetFilteredListDTO] = None,
        dto_options: Optional[MetricOptionsDTO] = None,
        related_filters: Optional[dict[str, dict[str, Any]]] = None,
    ) -> Sequence["MetricModel"]:
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
    async def delete(cls, session: AsyncSession, dto_get: MetricGetDTO) -> bool:
        """Удаление объекта MetricModel. Возвращает True, если объект найден и удалён, иначе False."""

        instance = await cls.get(session, dto_get)
        if not instance:
            logger.debug(f"Объект {cls.__name__} с данными для поиска {dto_get=} не найден и не удалён.")
            return False

        await session.delete(instance)
        await session.commit()

        logger.debug(f"Объект {cls.__name__} с данными для поиска {dto_get=} найден и удалён.")

        return True

    @classmethod
    def __build_relationship_options(
        cls,
        dto_options: Optional[MetricOptionsDTO] = None,
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
