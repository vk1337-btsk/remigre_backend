import asyncio
import logging
from typing import Any, Optional, Union

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.database.database import get_sessionmaker
from src.ms_location.schemas import (
    Body_GetCountryOrCityByCoordinates,
    CityDetailSchema,
    CoordinatesLocationsForMap,
    CountryDetailSchema,
    CountryListSchema,
    LocationOnlyListSchema,
    SearchLocationSchema,
)
from src.ms_location.services.db_location_service import DB_LocationService


logger = logging.getLogger(__name__)


class LocationService:

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] = Depends(get_sessionmaker)):
        """Инициализация основных параметров."""

        self.service_db = DB_LocationService(session_factory)

    #
    #
    # ============ Работа c локациями ============
    async def search_location_by_part_word(self, part_word: str) -> SearchLocationSchema:

        result_country = await self.service_db.get_country_by_part_name(part_word)
        result_country = [LocationOnlyListSchema.model_validate(el) for el in result_country]

        result_city = await self.service_db.get_city_by_part_name(part_word)
        result_city = [LocationOnlyListSchema.model_validate(el) for el in result_city]

        return SearchLocationSchema(country=result_country, cities=result_city)

    async def get_coordinates_for_map(self) -> CoordinatesLocationsForMap:
        """ """

        countries, cities = await asyncio.gather(
            self.service_db.get_coordinates_countries(),
            self.service_db.get_coordinates_cities(),
        )
        return CoordinatesLocationsForMap(countries=countries, cities=cities)

    async def get_id_country_or_city_by_coordinates(self, body: Body_GetCountryOrCityByCoordinates) -> int:
        """ """

        country_id, city_id = await self.service_db.get_country_and_city_id_by_coordinates(
            latitude=body.latitude, longitude=body.longitude
        )

        return city_id if body.type == "city" else country_id

    #
    #
    # ============ Работа со странами ============
    async def get_countries(self, only_list: bool) -> Union[list[CountryListSchema], list[CountryDetailSchema]]:

        if only_list:
            result = [CountryListSchema.model_validate(el) for el in await self.service_db.get_all_countries()]
            return result
        else:
            result = await self.service_db.get_all_countries()
            return result

    async def get_country(
        self,
        id: Optional[int] = None,
        # name: Optional[str] = None,
    ) -> CountryDetailSchema:

        if id:
            result = await self.service_db.get_country_by_id(id)
            return result
        else:
            raise HTTPException(status_code=500, detail="Неизвестная ошибка")

    #
    #
    # ============ Работа с городами ============
    async def get_cities(self, only_list: bool) -> Union[list[LocationOnlyListSchema], list[CityDetailSchema]]:

        if only_list:
            result = [LocationOnlyListSchema.model_validate(el) for el in await self.service_db.get_all_cities()]
            return result
        else:
            result = await self.service_db.get_all_cities()
            return result

    async def get_city(self, id: Optional[int] = None, coordinates: Optional[str] = None) -> CityDetailSchema:
        """Возвращает город по разным критериям"""

        if id:
            result = await self.service_db.get_city_by_id(id)
            return CityDetailSchema.model_validate(result)

        elif coordinates:
            result = await self.service_db.get_city_by_coordinates(coordinates=coordinates)
            return CityDetailSchema.model_validate(result)
        else:
            raise HTTPException(status_code=500, detail="Неизвестная ошибка")
