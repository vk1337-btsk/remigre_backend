import asyncio
import logging
from typing import Optional, Union

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.dependency import get_async_session, get_sessionmaker
from src.ms_location.schemas import (
    Body_GetCountryOrCityByCoordinates,
    CityDetailSchema,
    CountryDetailSchema,
    CountryListSchema,
    CountryShortInfoSchema,
    LocationMainInfoSchema,
    LocationOnlyListSchema,
)
from src.ms_location.services.db_location_service import DB_LocationService


logger = logging.getLogger(__name__)


class LocationService:

    def __init__(
        self,
        session: AsyncSession = Depends(get_async_session),
        session_factory: async_sessionmaker[AsyncSession] = Depends(get_sessionmaker),
    ):
        """Инициализация основных параметров."""

        self._async_session = session
        self._session_factory = session_factory
        self.service_db = DB_LocationService(session, session_factory)

    #
    #
    # ============ Общие методы для работы c локациями ============
    async def search_location_by_part_word(self, part_word: str) -> list[LocationMainInfoSchema]:
        """Осуществляет поиск стран/городов по их названию и возвращает список из вариантов."""

        return await self.service_db.get_locations_by_part_word(part_word)

    async def get_coordinates_locations_for_map(self, tolerance: Optional[float] = 0.1) -> dict:
        """Возвращает координаты и границы активных стран для карты"""

        tolerance = 0.1 if tolerance is None else tolerance
        return await self.service_db.get_coordinates_locations_for_map(tolerance)

    async def get_location_by_coordinates_from_map(
        self, body: Body_GetCountryOrCityByCoordinates
    ) -> LocationMainInfoSchema:
        """Возвращает основную информацию об объекте локации по его координатам."""

        row = await self.service_db.get_location_by_coordinates_from_map(
            location_type=body.type, latitude=body.latitude, longitude=body.longitude
        )

        return LocationMainInfoSchema(id=row["id"], type=body.type, name=row["name"], iso_code=row["iso_code"])

    #
    #
    # ============ Работа со странами ============
    async def get_list_countries(self) -> list[CountryShortInfoSchema]:
        """Возвращает список стран с основными метриками"""

        return await self.service_db.get_short_info_countries()

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

        else:
            raise HTTPException(status_code=500, detail="Неизвестная ошибка")
