import logging
from typing import Optional, Union

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.db_config import get_async_session
from src.ms_location.schemas.schemas import (
    CityDetailSchema,
    CountryDetailSchema,
    CountryListSchema,
    LocationOnlyListSchema,
    SearchLocationSchema,
)
from src.ms_location.services.db_location_service import DB_LocationService


logger = logging.getLogger(__name__)


class LocationService:

    def __init__(self, session: AsyncSession = Depends(get_async_session)):
        """Инициализация основных параметров."""

        self.service_db = DB_LocationService(session)

    #
    #
    # ============ Работа c локациями ============
    async def search_location_by_part_word(self, part_word: str) -> SearchLocationSchema:

        result_country = await self.service_db.get_country_by_part_name(part_word)
        result_country = [LocationOnlyListSchema.model_validate(el) for el in result_country]

        result_city = await self.service_db.get_city_by_part_name(part_word)
        result_city = [LocationOnlyListSchema.model_validate(el) for el in result_city]

        return SearchLocationSchema(country=result_country, cities=result_city)

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

    async def get_country(self, id: Optional[int] = None, name: Optional[str] = None) -> CountryDetailSchema:

        if id:
            result = await self.service_db.get_country_by_id(id)
            return result
        elif name:
            result = await self.service_db.get_country_by_name(name)
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

    async def get_city(
        self,
        id: Optional[int] = None,
        county_name: Optional[str] = None,
        city_name: Optional[str] = None,
        coordinates: Optional[str] = None,
    ) -> CityDetailSchema:
        """Возвращает город по разным критериям"""

        if id:
            result = await self.service_db.get_city_by_id(id)
            return CityDetailSchema.model_validate(result)
        elif county_name and city_name:
            result = await self.service_db.get_city_by_country_and_city_name(
                country_name=county_name, city_name=city_name
            )
            return CityDetailSchema.model_validate(result)
        elif coordinates:
            result = await self.service_db.get_city_by_coordinates(coordinates=coordinates)
            return CityDetailSchema.model_validate(result)
        else:
            raise HTTPException(status_code=500, detail="Неизвестная ошибка")
