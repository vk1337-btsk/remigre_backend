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
    Text,
    UniqueConstraint,
    and_,
    func,
    or_,
    select,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, selectinload, with_loader_criteria

from src.core.database.base_crud_mixin import BaseCRUDMixin
from src.core.database.base_dto import GetFilteredListDTO
from src.core.database.base_models import AbstractBaseModel
from src.ms_location.dto.city_dto import (
    CityCreateDTO,
    CityGetDTO,
    CityOptionsDTO,
    CityUpdateDTO,
)


logger = logging.getLogger(__name__)


class CityModel(AbstractBaseModel):
    """Модель с данными о городе"""

    __tablename__ = "loc_city"

    __table_args__ = (
        UniqueConstraint("country_id", "name", name="uq_city_country_name"),
        UniqueConstraint("country_id", "name_eng", name="uq_city_country_name_eng"),
        UniqueConstraint("latitude", "longitude", name="uq_city_coordinates"),
        #
        # Ограничение: latitude от -90 до 90, longitude от -180 до 180
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_city_latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_city_longitude_range"),
        #
        # Ограничение: в одной стране только один город со статусом is_capital = True
        CheckConstraint(
            """
            NOT is_capital OR
            (
                SELECT COUNT(*) FROM city c
                WHERE c.country_id = country_id AND c.is_capital = TRUE
            ) = 1
            """,
            name="ck_one_capital_per_country",
        ),
        {"comment": "Таблица городов"},
    )

    # Идентификатор города
    id = Column(Integer, primary_key=True, index=True, comment="ID города")
    country_id = Column(
        Integer, ForeignKey("loc_country.id", ondelete="CASCADE"), nullable=False, index=True, comment="ID страны"
    )
    region_id = Column(
        Integer, ForeignKey("loc_region.id", ondelete="CASCADE"), nullable=True, index=True, comment="ID региона"
    )
    name = Column(String(255), nullable=False, index=True, comment="Название города")
    name_eng = Column(String(255), nullable=False, index=True, comment="Название города ENG")

    # Местоположение
    latitude = Column(Float, nullable=False, index=True, comment="Широта")
    longitude = Column(Float, nullable=False, index=True, comment="Долгота")

    # Характеристика города
    is_capital = Column(Boolean, nullable=False, default=False, server_default=text("false"), comment="Столица")
    timezone = Column(String(100), nullable=True, comment="Часовой пояс")
    population = Column(Integer, nullable=True, comment="Население города")
    language = Column(String(50), nullable=True, comment="Основной язык")
    climate = Column(String(100), nullable=True, comment="Климат")
    description = Column(Text, nullable=True, comment="Описание города")

    @hybrid_property
    def coordinates(self):
        """Координаты"""
        return f"{self.latitude},{self.longitude}"

    # Важные статусы
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"), comment="Отображение города")

    # Обратная связь
    country = relationship("CountryModel", back_populates="cities", lazy="noload", foreign_keys=[country_id])
    region = relationship("RegionModel", back_populates="cities", lazy="noload", foreign_keys=[region_id])
    data_entries = relationship("MetricDataModel", back_populates="city", lazy="noload", cascade="all, delete-orphan")

    # ======== Классовые методы ========
    @classmethod
    def _get_relationship_map(cls) -> dict[str, tuple[str, Any]]:
        """Возвращает отображение DTO-флагов на отношения модели"""

        return {
            "with_region": ("regions", cls.region),
            "with_country": ("cities", cls.country),
            "with_data": ("data_entries", cls.data_entries),
        }

    @classmethod
    async def create(cls, session: AsyncSession, dto_create: CityCreateDTO) -> "CityModel":
        """Создание нового объекта CityModel."""

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
        dto_get: CityGetDTO,
        dto_update: CityUpdateDTO,
        dto_options: Optional[CityOptionsDTO] = None,
    ) -> Optional["CityModel"]:
        """Обновление существующего объекта CityModel, если не найдено - None."""

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
    async def exists(cls, session: AsyncSession, dto_get: CityGetDTO) -> bool:
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
        dto_get: CityGetDTO,
        dto_options: Optional[CityOptionsDTO] = None,
        related_filters: Optional[dict[str, dict[str, Any]]] = None,
    ) -> Optional["CityModel"]:
        """Возвращает объект CityModel с опциональной подгрузкой связанных сущностей, если не найдено - None."""

        stmt = select(cls)

        # Определения условий поиска объекта
        if dto_get.id:
            stmt = stmt.where(cls.id == dto_get.id)
        elif dto_get.country_id and dto_get.name:
            stmt = stmt.where(and_(cls.country_id == dto_get.country_id, cls.name == dto_get.name))
        elif dto_get.country_id and dto_get.name_eng:
            stmt = stmt.where(and_(cls.country_id == dto_get.country_id, cls.name_eng == dto_get.name_eng))
        elif dto_get.coordinates:
            latitude, longitude = dto_get.coordinates.split(",")
            latitude, longitude = float(latitude), float(longitude)
            stmt = stmt.where(
                or_(
                    and_(cls.latitude == latitude, cls.longitude == longitude),
                    and_(cls.latitude == longitude, cls.longitude == latitude),
                )
            )
        else:
            ValueError(f"Не хватает данных для поиска уникального города: {dto_get}")

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
        dto_options: Optional[CityOptionsDTO] = None,
        related_filters: Optional[dict[str, dict[str, Any]]] = None,
    ) -> Sequence["CityModel"]:
        """Получить список объектов CityModel с возможностью:
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
                    stmt = stmt.where(func.lower(column).like(func.lower(f"{value}%")))

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
    async def delete(cls, session: AsyncSession, dto_get: CityGetDTO) -> bool:
        """Удаление объекта CityModel. Возвращает True, если объект найден и удалён, иначе False."""

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
        dto_options: Optional[CityOptionsDTO] = None,
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
