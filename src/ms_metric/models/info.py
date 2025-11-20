import logging
from typing import Any, Optional, Sequence

from sqlalchemy import (
    Boolean,
    Column,
    Enum,
    Integer,
    String,
    Text,
    UniqueConstraint,
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

from src.core.database import AbstractBaseModel, GetFilteredListDTO
from src.ms_metric.dto import (
    MetricInfoCreateDTO,
    MetricInfoGetDTO,
    MetricInfoOptionsDTO,
    MetricInfoUpdateDTO,
)
from src.ms_metric.enums import CategoryMetricEnum, TypeDataEnum


logger = logging.getLogger(__name__)


class MetricInfoModel(AbstractBaseModel):
    """Модель метрики"""

    __tablename__ = "metric_info"

    __table_args__ = (
        # Уникальное ограничение: slug
        UniqueConstraint("slug", name="uq_metric_info_slug"),
        {"comment": "Индикатор метрики"},
    )

    id = Column(Integer, primary_key=True, comment="ID")

    # Информация о метрике
    slug = Column(String(255), nullable=False, index=True, comment="Slug (текстовой идентификатор)")
    name = Column(String(255), nullable=False, comment="Название")
    description = Column(Text, nullable=True, comment="Описание")
    category = Column(Enum(CategoryMetricEnum, name="category_metric_enum"), nullable=False, comment="Категория")

    # Информация об источнике метрики
    source_name = Column(String(255), nullable=True, comment="Источник")
    source_url = Column(String(512), nullable=True, comment="URL источника")
    type_data = Column(Enum(TypeDataEnum, name="type_data_enum"), nullable=False, comment="Тип данных")

    # Дополнительно
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"), comment="Флаг активности")
    add_info = Column(JSONB, nullable=True, comment="Доп. информация")

    # ======== Обратная связь ========
    series = relationship("MetricSeriesModel", back_populates="metric", lazy="noload", cascade="all, delete-orphan")

    @classmethod
    def _get_relationship_map(cls) -> dict[str, tuple[str, Any]]:
        """Отображение DTO-флагов на отношения модели"""

        return {
            "with_series": ("series", cls.series),
        }

    # ======== Классовые методы ========
    @classmethod
    async def get(
        cls,
        session: AsyncSession,
        dto_get: MetricInfoGetDTO,
        dto_options: Optional[MetricInfoOptionsDTO] = None,
        related_filters: Optional[dict[str, dict[str, Any]]] = None,
    ) -> Optional["MetricInfoModel"]:
        """Возвращает объект MetricInfoModel с опциональной подгрузкой связанных сущностей, если не найдено - None."""

        stmt = select(cls)

        # Условия поиска
        if dto_get.id is not None:
            stmt = stmt.where(cls.id == dto_get.id)
        elif dto_get.slug is not None:
            stmt = stmt.where(cls.slug == dto_get.slug)
        else:
            raise ValueError(f"Не хватает данных для поиска индикатора: {dto_get}")

        # Подгрузка связей
        stmt = stmt.options(*cls.__build_relationship_options(dto_options, related_filters))

        result = await session.execute(stmt.limit(1))

        logger.debug(f"Получение объекта {cls.__name__} по данным: {dto_get=}.")

        return result.scalar_one_or_none()

    @classmethod
    async def create(cls, session: AsyncSession, dto_create: MetricInfoCreateDTO) -> "MetricInfoModel":
        """Создание нового индикатора."""

        instance = cls(**dto_create.model_dump(exclude_unset=True))
        session.add(instance)
        await session.commit()
        await session.refresh(instance)

        logger.debug(f"Создан объект {cls.__name__}: {instance}")
        return instance

    @classmethod
    async def get_or_create(cls, session: AsyncSession, dto_create: MetricInfoCreateDTO) -> "MetricInfoModel":
        """Получает существующий индикатор или создаёт новый, если не найден."""

        create_data = dto_create.model_dump(exclude_unset=True, exclude_none=True)

        stmt = select(cls)

        # Сравнение обычных полей
        for field, value in create_data.items():
            if field == "add_info":
                continue
            if hasattr(cls, field):
                stmt = stmt.where(getattr(cls, field) == value)

        # Сравнение поля add_info JSONB по ключам и значениям
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

        # Проверяем, есть ли такой объект
        result = await session.execute(stmt.limit(1))
        instance = result.scalar_one_or_none()

        if instance:
            logger.debug(f"[{cls.__name__}.get_or_create] Найден объект: {instance.id}")
            return instance

        instance = cls(**create_data)
        session.add(instance)
        await session.commit()
        await session.refresh(instance)

        logger.debug(f"[{cls.__name__}.get_or_create] Создан новый объект: {instance.id}")
        return instance

    @classmethod
    async def update(
        cls,
        session: AsyncSession,
        dto_get: MetricInfoGetDTO,
        dto_update: MetricInfoUpdateDTO,
        dto_options: Optional[MetricInfoOptionsDTO] = None,
    ) -> Optional["MetricInfoModel"]:
        """Обновление существующего индикатора, если не найдено - None."""

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
    async def exists(cls, session: AsyncSession, dto_get: MetricInfoGetDTO) -> bool:
        """Возвращает True, если индикатор существует, иначе False."""

        stmt = select(cls.id)

        # Определения условий поиска объекта
        filters = dto_get.model_dump(exclude_unset=True)
        for field, value in filters.items():
            column = getattr(cls, field, None)
            if column is not None:
                stmt = stmt.where(column == value)

        result = await session.execute(stmt.limit(1))
        return result.scalar_one_or_none() is not None

    @classmethod
    async def get_all_filtered(
        cls,
        session: AsyncSession,
        dto_filters: Optional[GetFilteredListDTO] = None,
        dto_options: Optional[MetricInfoOptionsDTO] = None,
        related_filters: Optional[dict[str, dict[str, Any]]] = None,
    ) -> Sequence["MetricInfoModel"]:
        """Получить список индикаторов с фильтрацией и подгрузкой связей."""

        stmt = select(cls)

        # Осуществляем фильтрацию
        if dto_filters:

            # Точное сравнение
            filters = dto_filters.filters or {}
            for key, value in filters.items():
                column = getattr(cls, key, None)
                if column is not None:
                    stmt = stmt.where(column == value)

            # LIKE-фильтры
            like_filters = dto_filters.like_filters or {}
            for key, value in like_filters.items():
                column = getattr(cls, key, None)
                if column is not None:
                    stmt = stmt.where(func.lower(column).like(f"%{value.lower()}%"))

            # OR LIKE-фильтрация
            or_like_filters = dto_filters.or_like_filters or {}
            if or_like_filters:
                conditions = []
                for key, value in or_like_filters.items():
                    column = getattr(cls, key, None)
                    if column is not None:
                        conditions.append(column.ilike(f"{value}%"))
                if conditions:
                    stmt = stmt.where(or_(*conditions))

            # IN-фильтры
            in_filters = dto_filters.in_filters or {}
            for key, values in in_filters.items():
                column = getattr(cls, key, None)
                if column is not None:
                    stmt = stmt.where(column.in_(values))

            # пагинация
            if dto_filters.offset:
                stmt = stmt.offset(dto_filters.offset)
            if dto_filters.limit:
                stmt = stmt.limit(dto_filters.limit)

        stmt = stmt.order_by(cls.id)
        stmt = stmt.options(*cls.__build_relationship_options(dto_options, related_filters))

        result = await session.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def delete(cls, session: AsyncSession, dto_get: MetricInfoGetDTO) -> bool:
        """Удаление индикатора. Возвращает True, если объект найден и удалён, иначе False."""

        instance = await cls.get(session, dto_get)
        if not instance:
            logger.debug(f"Индикатор {cls.__name__} с данными {dto_get=} не найден и не удалён.")
            return False

        await session.delete(instance)
        await session.commit()

        logger.debug(f"Индикатор {cls.__name__} с данными {dto_get=} найден и удалён.")
        return True

    # ======== Вспомогательные методы ========
    @classmethod
    def __build_relationship_options(
        cls,
        dto_options: Optional[MetricInfoOptionsDTO] = None,
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
            if getattr(dto_options, dto_field, False):
                options.append(selectinload(relation_attr))
                if related_filters and relation_name in related_filters:
                    model_cls = relation_attr.property.mapper.class_
                    criteria = _build_filter_conditions(model_cls, related_filters[relation_name])
                    if criteria is not None:
                        options.append(with_loader_criteria(model_cls, criteria))

        return options
