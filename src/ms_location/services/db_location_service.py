import logging
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.base_dto import GetFilteredListDTO
from src.ms_location.dto import (
    CityGetDTO,
    CityOptionsDTO,
    CountryGetDTO,
    CountryOptionsDTO,
)
from src.ms_location.models import CityModel, CountryModel, RegionModel
from src.ms_location.schemas.schemas import CityDetailSchema, CountryDetailSchema


logger = logging.getLogger(__name__)


class DB_LocationService:

    def __init__(self, async_session: AsyncSession):
        """Инициализация основных параметров."""

        self._async_session = async_session

    #
    #
    # ============ Работа со странами ============
    async def get_all_countries(self) -> list[CountryDetailSchema]:

        result = await CountryModel.get_all_filtered(
            self._async_session, dto_filters=GetFilteredListDTO(filters={"is_active": True})
        )
        return [CountryDetailSchema.from_orm_with_geojson(country) for country in result]

    async def get_country_by_part_name(self, part_name: str):

        result = await CountryModel.get_all_filtered(
            self._async_session,
            dto_filters=GetFilteredListDTO(or_like_filters={"name": part_name, "name_eng": part_name}),
        )
        return [CountryDetailSchema.from_orm_with_geojson(country) for country in result]

    async def get_country_by_id(self, county_id: int) -> CountryDetailSchema:

        result = await CountryModel.get(self._async_session, dto_get=CountryGetDTO(id=county_id))
        if result:
            return CountryDetailSchema.from_orm_with_geojson(result)
        raise HTTPException(status_code=404, detail=f"Страна с {county_id=} не найдена")

    async def get_country_by_name(self, name: str) -> CountryDetailSchema:

        result = await CountryModel.get(self._async_session, dto_get=CountryGetDTO(name=name))
        if result:
            return CountryDetailSchema.from_orm_with_geojson(result)
        raise HTTPException(status_code=404, detail=f"Страна с названием {name=} не найдена")

    #
    #
    # ============ Работа с городами ============
    async def get_all_cities(self) -> list[CityDetailSchema]:

        result = await CityModel.get_all_filtered(
            self._async_session, dto_filters=GetFilteredListDTO(filters={"is_active": True})
        )
        return [CityDetailSchema.model_validate(country) for country in result]

    async def get_city_by_part_name(self, part_name: str):

        result = await CityModel.get_all_filtered(
            self._async_session,
            dto_filters=GetFilteredListDTO(or_like_filters={"name": part_name, "name_eng": part_name}),
        )
        return [CityDetailSchema.model_validate(country) for country in result]

    async def get_city_by_id(self, city_id: int) -> CityDetailSchema:

        result = await CityModel.get(self._async_session, dto_get=CityGetDTO(id=city_id))
        if result:
            return CityDetailSchema.model_validate(result)
        raise HTTPException(status_code=404, detail=f"Город с {city_id=} не найдена")

    async def get_city_by_coordinates(self, coordinates: str) -> CityDetailSchema:

        result = await CityModel.get(self._async_session, dto_get=CityGetDTO(coordinates=coordinates))
        if result:
            return CityDetailSchema.model_validate(result)
        raise HTTPException(status_code=404, detail=f"Город с {coordinates=} не найдена")

    async def get_city_by_country_and_city_name(self, country_name: str, city_name: str) -> CityDetailSchema:
        """Возвращает город по названию страны и города."""

        async with self._async_session as session:
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
