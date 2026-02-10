import json
import logging
from datetime import datetime
from typing import Literal, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import and_, func, literal, select, text, union_all
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.database.base_dto import GetFilteredListDTO
from src.ms_location.dto import CityGetDTO, CountryGetDTO
from src.ms_location.models import CityModel, CountryModel
from src.ms_location.schemas import (
    CityDetailSchema,
    CountryDetailSchema,
    CountryShortInfoSchema,
    LocationMainInfoSchema,
)
from src.ms_metric.models import (
    MetricDataModel,
    MetricInfoModel,
    MetricPeriodModel,
    MetricSeriesModel,
)


logger = logging.getLogger(__name__)


class DB_LocationService:

    def __init__(
        self,
        session: AsyncSession,
        session_factory: async_sessionmaker[AsyncSession],
    ):
        """Инициализация основных параметров."""

        self._async_session = session
        self._session_factory = session_factory

    #
    #
    # ============ Операции с локациями ============
    async def get_locations_by_part_word(self, part_word: str) -> list[LocationMainInfoSchema]:
        """Осуществляет поиск стран и городов по части их названия"""

        search = f"%{part_word}%"

        # Запрос для стран
        country_stmt = select(
            CountryModel.id.label("id"),
            literal("country").label("type"),
            CountryModel.name.label("name"),
            CountryModel.iso_alpha_2.label("iso_code"),
        ).where(
            CountryModel.is_active.is_(True),
            CountryModel.name.ilike(search),
        )

        # Запрос для городов
        city_stmt = (
            select(
                CityModel.id.label("id"),
                literal("city").label("type"),
                CityModel.name.label("name"),
                CountryModel.iso_alpha_2.label("iso_code"),
            )
            .join(CountryModel, CityModel.country_id == CountryModel.id)
            .where(
                CityModel.is_active.is_(True),
                CityModel.name.ilike(search),
            )
        )

        stmt = union_all(country_stmt, city_stmt)  # Объединяем запросы
        result = await self._async_session.execute(stmt)  # Получаем результат

        return [LocationMainInfoSchema.model_validate(obj) for obj in result.mappings().all()]

    async def get_coordinates_locations_for_map(self, tolerance: float) -> dict:
        """Возвращает координаты и границы активных стран для карты"""

        sql = text(
            """
            SELECT jsonb_build_object(
                'countries', jsonb_build_object(
                    'type', 'FeatureCollection',
                    'features', countries.features
                ),
                'cities', jsonb_build_object(
                    'type', 'FeatureCollection',
                    'features', cities.features
                )
            ) AS geojson
            FROM
            (
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'type', 'Feature',
                        'geometry', ST_AsGeoJSON(
                            COALESCE(
                                ST_SimplifyPreserveTopology(c.geometry, :tolerance),
                                c.geometry
                            )
                        )::jsonb,
                        'properties', jsonb_build_object(
                            'id', c.id,
                            'name', c.name
                        )
                    )
                ) AS features
                FROM loc_country c
                WHERE c.is_active = TRUE
                AND c.geometry IS NOT NULL
                AND ST_IsValid(c.geometry)
            ) countries,
            (
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'type', 'Feature',
                        'geometry', ST_AsGeoJSON(
                            ST_SetSRID(ST_MakePoint(ci.longitude, ci.latitude), 4326)
                        )::jsonb,
                        'properties', jsonb_build_object(
                            'id', ci.id,
                            'name', ci.name,
                            'is_capital', ci.is_capital
                        )
                    )
                ) AS features
                FROM loc_city ci
                WHERE ci.is_active = TRUE
            ) cities;
            """
        )
        result = await self._async_session.execute(sql, {"tolerance": tolerance})
        return result.scalar_one()

    async def get_location_by_coordinates_from_map(
        self,
        location_type: Literal["city", "country"],
        latitude: float,
        longitude: float,
    ):
        """Осуществляет поиск страны или города по его координатам."""

        point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)

        if location_type == "city":
            stmt = (
                select(
                    CityModel.id.label("id"),
                    CityModel.name.label("name"),
                    CountryModel.iso_alpha_2.label("iso_code"),
                )
                .join(CountryModel, CityModel.country_id == CountryModel.id)
                .where(
                    and_(
                        CityModel.latitude == latitude,
                        CityModel.longitude == longitude,
                        CityModel.is_active.is_(True),
                    )
                )
                .limit(1)
            )

        else:  # country
            stmt = (
                select(
                    CountryModel.id.label("id"),
                    CountryModel.name.label("name"),
                    CountryModel.iso_alpha_2.label("iso_code"),
                )
                .where(
                    and_(
                        CountryModel.is_active.is_(True),
                        func.ST_Contains(CountryModel.geometry, point),
                    )
                )
                .limit(1)
            )

        result = await self._async_session.execute(stmt)
        row = result.mappings().first()

        if not row:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"{'Город' if location_type == 'city' else 'Страна'} "
                    f"по координатам ({latitude}, {longitude}) не найден(а)."
                ),
            )

        return row

    #
    #
    # ============ Работа со странами ============
    async def get_main_info_countries(self) -> list[LocationMainInfoSchema]:
        """Получает и возвращает из БД список с основной информацией о странах."""

        stmt = select(
            CountryModel.id,
            CountryModel.name,
            CountryModel.iso_alpha_2,
        ).where(
            CountryModel.is_active == True,
        )

        result = await self._async_session.execute(stmt)
        rows = result.all()
        return [LocationMainInfoSchema.model_validate(obj) for obj in rows]

    async def get_short_info_countries(self) -> list[CountryShortInfoSchema]:
        """Получает и возвращает из БД список с краткой информацией о странах."""

        current_year = datetime.utcnow().year

        stmt = (
            select(
                CountryModel.id,
                CountryModel.name,
                CountryModel.iso_alpha_2,
                CountryModel.currency,
                CountryModel.population,
                func.avg(MetricDataModel.value_float).label("metric_1_avg"),
            )
            .select_from(CountryModel)
            .outerjoin(
                MetricDataModel,
                MetricDataModel.country_id == CountryModel.id,
            )
            .outerjoin(
                MetricSeriesModel,
                MetricSeriesModel.id == MetricDataModel.series_id,
            )
            .outerjoin(
                MetricInfoModel,
                and_(
                    MetricInfoModel.id == MetricSeries  Model.metric_id,
                    MetricInfoModel.id == 1,  # ← ВАЖНО: тут
                ),
            )
            .outerjoin(
                MetricPeriodModel,
                and_(
                    MetricPeriodModel.id == MetricDataModel.period_id,
                    MetricPeriodModel.period_year == current_year,  # ← и тут
                ),
            )
            .where(
                CountryModel.is_active.is_(True),
            )
            .group_by(
                CountryModel.id,
                CountryModel.name,
                CountryModel.iso_alpha_2,
                CountryModel.currency,
                CountryModel.population,
            )
        )

        result = await self._async_session.execute(stmt)

        rows = result.all()

        return [
            CountryShortInfoSchema(
                id=row.id,
                name=row.name,
                iso_alpha_2=row.iso_alpha_2,
                currency=row.currency,
                population=row.population,
                metrics={
                    "metric_1_avg": row.metric_1_avg,
                },
            )
            for row in rows
        ]

    async def get_country_by_id(self, county_id: int) -> CountryDetailSchema:

        async with self._session_factory() as session:

            result = await CountryModel.get(session, dto_get=CountryGetDTO(id=county_id))
            if result:
                return CountryDetailSchema.from_orm_with_geojson(result)
            raise HTTPException(status_code=404, detail=f"Страна с {county_id=} не найдена")

    #
    #
    # ============ Работа с городами ============
    async def get_all_cities(self) -> list[CityDetailSchema]:

        async with self._session_factory() as session:

            result = await CityModel.get_all_filtered(
                session, dto_filters=GetFilteredListDTO(filters={"is_active": True})
            )
            return [CityDetailSchema.model_validate(country) for country in result]

    async def get_city_by_id(self, city_id: int) -> CityDetailSchema:

        async with self._session_factory() as session:
            result = await CityModel.get(session, dto_get=CityGetDTO(id=city_id))
            if result:
                return CityDetailSchema.model_validate(result)
            raise HTTPException(status_code=404, detail=f"Город с {city_id=} не найдена")
