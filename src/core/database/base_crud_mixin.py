import logging
from typing import Any, Optional, Sequence, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy import and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, with_loader_criteria

from src.core.database.base_dto import GetFilteredListDTO


logger = logging.getLogger(__name__)


T = TypeVar("T", bound="BaseCRUDMixin")


class BaseCRUDMixin:
    """Универсальный миксин для CRUD-операций с поддержкой DTO"""

    # --- Переопределяется в дочерней модели ---
    @classmethod
    def _get_relationship_map(cls) -> dict[str, tuple[str, Any]]:
        """Возвращает отображение DTO-флагов на отношения модели"""

        return {}

    # --- CRUD ---
    @classmethod
    async def create(cls: Type[T], session: AsyncSession, dto_create: BaseModel) -> T:
        """Создание нового объекта."""

        instance = cls(**dto_create.model_dump(exclude_unset=True))
        session.add(instance)

        await session.commit()
        await session.refresh(instance)

        logger.debug(f"Создан объект {cls.__name__}: {instance}")

        return instance

    @classmethod
    async def update(
        cls: Type[T],
        session: AsyncSession,
        dto_get: BaseModel,
        dto_update: BaseModel,
        dto_options: Optional[BaseModel] = None,
    ) -> Optional[T]:
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
    async def delete(cls: Type[T], session: AsyncSession, dto_get: BaseModel) -> bool:
        """Удаление объекта. Возвращает True, если объект найден и удалён."""

        instance = await cls.get(session, dto_get)
        if not instance:
            logger.debug(f"Объект {cls.__name__} с данными для поиска {dto_get=} не найден и не удалён.")
            return False

        await session.delete(instance)
        await session.commit()

        logger.debug(f"Объект {cls.__name__} с данными для поиска {dto_get=} найден и удалён.")

        return True

    @classmethod
    async def exists(cls: Type[T], session: AsyncSession, dto_get: BaseModel) -> bool:
        """Возвращает True, если объект существует."""

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
        cls: Type[T],
        session: AsyncSession,
        dto_get: BaseModel,
        dto_options: Optional[BaseModel] = None,
        related_filters: Optional[dict[str, dict[str, Any]]] = None,
    ) -> Optional[T]:
        """Возвращает объект с опциональной подгрузкой связанных сущностей, если не найдено - None."""

        stmt = select(cls)

        # Определения условий поиска объекта
        filters = dto_get.model_dump(exclude_unset=True)
        for field, value in filters.items():
            column = getattr(cls, field, None)
            if column is not None:
                stmt = stmt.where(column == value)

        # Опциональная подгрузка связей
        stmt = stmt.options(*cls.__build_relationship_options(dto_options, related_filters))

        result = await session.execute(stmt.limit(1))

        logger.debug(f"Получение объекта {cls.__name__} - {result=} по данным: {dto_get=}.")

        return result.scalar_one_or_none()

    @classmethod
    async def get_all_filtered(
        cls: Type[T],
        session: AsyncSession,
        dto_filters: Optional[GetFilteredListDTO] = None,
        dto_options: Optional[BaseModel] = None,
        related_filters: Optional[dict[str, dict[str, Any]]] = None,
    ) -> Sequence[T]:
        """Получить список объектов с возможностью:
        - фильтрации по точным, LIKE- и IN-условиям с поддержкой пагинации по dto_filters.
        Если не задан - вернёт все объекты
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
    def __build_relationship_options(
        cls,
        dto_options: Optional[BaseModel] = None,
        related_filters: Optional[dict[str, dict[str, Any]]] = None,
    ) -> list:
        """Формирует SQLAlchemy options() для подгрузки связей с фильтрацией"""

        def _build_filter_conditions(model_cls, filters: dict[str, Any]):
            """Строит SQLAlchemy выражение AND(...) по фильтрам"""

            conditions = []
            for field, value in filters.items():
                column = getattr(model_cls, field, None)
                if column is not None:
                    conditions.append(column == value)

            return and_(*conditions) if conditions else None

        if not dto_options:
            return []

        options = []

        for dto_field, (relation_name, relation_attr) in cls._get_relationship_map().items():
            if getattr(dto_options, dto_field, False):
                options.append(selectinload(relation_attr))

                if related_filters and relation_name in related_filters:
                    model_cls = relation_attr.property.mapper.class_
                    criteria = _build_filter_conditions(model_cls, related_filters[relation_name])
                    if criteria is not None:
                        options.append(with_loader_criteria(model_cls, criteria))

        return options
