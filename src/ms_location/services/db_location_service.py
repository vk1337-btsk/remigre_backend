import json
import logging
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.database.base_dto import GetFilteredListDTO
from src.ms_location.dto import (
    CityGetDTO,
    CityOptionsDTO,
    CountryGetDTO,
    CountryOptionsDTO,
)
from src.ms_location.models import CityModel, CountryModel
from src.ms_location.schemas import (
    CityDetailSchema,
    CoordinatesSchema,
    CountryDetailSchema,
)


logger = logging.getLogger(__name__)


class DB_LocationService:

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        """Инициализация основных параметров."""

        self._session_factory = session_factory

    #
    #
    # ============ Работа со странами ============
    async def get_all_countries(self) -> list[CountryDetailSchema]:

        async with self._session_factory() as session:
            result = await CountryModel.get_all_filtered(
                session, dto_filters=GetFilteredListDTO(filters={"is_active": True})
            )
            return [CountryDetailSchema.from_orm_with_geojson(country) for country in result]

    async def get_country_by_part_name(self, part_name: str):

        async with self._session_factory() as session:

            result = await CountryModel.get_all_filtered(
                session,
                dto_filters=GetFilteredListDTO(or_like_filters={"name": part_name, "name_eng": part_name}),
            )
            return [CountryDetailSchema.from_orm_with_geojson(country) for country in result]

    async def get_country_by_id(self, county_id: int) -> CountryDetailSchema:

        async with self._session_factory() as session:

            result = await CountryModel.get(session, dto_get=CountryGetDTO(id=county_id))
            if result:
                return CountryDetailSchema.from_orm_with_geojson(result)
            raise HTTPException(status_code=404, detail=f"Страна с {county_id=} не найдена")

    async def get_country_by_name(self, name: str) -> CountryDetailSchema:

        async with self._session_factory() as session:

            result = await CountryModel.get(session, dto_get=CountryGetDTO(name=name))
            if result:
                return CountryDetailSchema.from_orm_with_geojson(result)
            raise HTTPException(status_code=404, detail=f"Страна с названием {name=} не найдена")

    async def get_coordinates_countries(self, tolerance: float = 0.1) -> list[CoordinatesSchema]:

        async with self._session_factory() as session:

            sql = text(
                """
                SELECT 
                    id,
                    name,
                    ST_AsGeoJSON(ST_SimplifyPreserveTopology(geometry, :tolerance)) AS geometry
                FROM loc_country
                WHERE is_active = TRUE
                """
            )
            rows = (await session.execute(sql, {"tolerance": tolerance})).mappings().all()

            coordinates_countries = []
            for r in rows:
                if not r["geometry"]:
                    continue
                geometry = json.loads(r["geometry"])
                coordinates_countries.append(
                    CoordinatesSchema(
                        id=r["id"],
                        name=r["name"],
                        type=geometry["type"],
                        coordinates=geometry["coordinates"],
                    )
                )
            return coordinates_countries

    #
    #
    # ============ Работа с городами ============
    async def get_all_cities(self) -> list[CityDetailSchema]:

        async with self._session_factory() as session:

            result = await CityModel.get_all_filtered(
                session, dto_filters=GetFilteredListDTO(filters={"is_active": True})
            )
            return [CityDetailSchema.model_validate(country) for country in result]

    async def get_city_by_part_name(self, part_name: str):

        async with self._session_factory() as session:
            result = await CityModel.get_all_filtered(
                session,
                dto_filters=GetFilteredListDTO(or_like_filters={"name": part_name, "name_eng": part_name}),
            )
            return [CityDetailSchema.model_validate(country) for country in result]

    async def get_city_by_id(self, city_id: int) -> CityDetailSchema:

        async with self._session_factory() as session:
            result = await CityModel.get(session, dto_get=CityGetDTO(id=city_id))
            if result:
                return CityDetailSchema.model_validate(result)
            raise HTTPException(status_code=404, detail=f"Город с {city_id=} не найдена")

    async def get_city_by_coordinates(self, coordinates: str) -> CityDetailSchema:

        async with self._session_factory() as session:
            result = await CityModel.get(session, dto_get=CityGetDTO(coordinates=coordinates))
            if result:
                return CityDetailSchema.model_validate(result)
            raise HTTPException(status_code=404, detail=f"Город с {coordinates=} не найдена")

    async def get_city_by_country_and_city_name(self, country_name: str, city_name: str) -> CityDetailSchema:
        """Возвращает город по названию страны и города."""

        async with self._session_factory() as session:
            # 1. Проверим страну
            country = await CountryModel.get(session, CountryGetDTO(name_eng=country_name))
            if not country:
                raise HTTPException(
                    status_code=404,
                    detail=f"Страна '{country_name}' не найдена",
                )
            country = CountryDetailSchema.model_validate(country)

            # 2. Проверим город
            city = await CityModel.get(
                session,
                CityGetDTO(country_id=country.id, name=city_name),
                dto_options=CityOptionsDTO(with_country=True, with_region=True),
            )
            if not city:
                raise HTTPException(
                    status_code=404,
                    detail=f"Город '{city_name}' в стране '{country_name}' не найден",
                )

            # 3. Преобразуем в schema
            return CityDetailSchema.model_validate(city, from_attributes=True)

    async def get_coordinates_cities(self) -> list[CoordinatesSchema]:

        async with self._session_factory() as session:

            stmt = select(CityModel.id, CityModel.name, CityModel.latitude, CityModel.longitude).where(
                CityModel.is_active.is_(True)
            )
            result = await session.execute(stmt)
            rows = result.all()

            coordinates_cities = []
            for r in rows:
                data = r._mapping
                coordinates_cities.append(
                    CoordinatesSchema(
                        id=data["id"],
                        name=data["name"],
                        type="Point",
                        coordinates=[data["longitude"], data["latitude"]],
                    )
                )
            return coordinates_cities
