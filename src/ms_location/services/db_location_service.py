import json
import logging
from typing import Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.database.base_dto import GetFilteredListDTO
from src.ms_location.dto import (
    CityGetDTO,
    CountryGetDTO,
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
    # ============ Операции с локациями ============
    async def get_country_and_city_id_by_coordinates(self, latitude: float, longitude: float) -> Tuple[int, int]:
        """Возвращает id города и страны по координатам

        Args:
            latitude (float): _description_
            longitude (float): _description_

        Raises:
            HTTPException: _description_

        Returns:
            Tuple[int, int]: ID страны, ID города
        """

        async with self._session_factory() as session:
            stmt = (
                select(CityModel.id, CityModel.country_id)
                .where(
                    and_(
                        CityModel.latitude == latitude,
                        CityModel.longitude == longitude,
                        CityModel.is_active == True,
                    )
                )
                .limit(1)
            )

            result = await session.execute(stmt)
            row = result.first()

            if not row:
                raise HTTPException(
                    status_code=404, detail=f"Город с координатами ({latitude}, {longitude}) не найден."
                )

            return row.country_id, row.id

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
