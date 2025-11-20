import logging
from typing import Union

from fastapi import APIRouter, Depends, Path, Query

from src.ms_location.schemas.schemas import (
    CityDetailSchema,
    CountryDetailSchema,
    CountryListSchema,
    LocationOnlyListSchema,
    SearchLocationSchema,
)
from src.ms_location.services.location_service import LocationService


logger = logging.getLogger(__name__)


router = APIRouter(prefix="/location", tags=["Location"])


@router.get(
    "/search",
    summary="Поиск по названию страны/города",
    description="Начинаешь вводить название -> получаешь варианты",
)
async def get_search(
    name_search: str = Query(min_length=3, title="Название и/или часть названия страны/города"),
    service: LocationService = Depends(),
) -> SearchLocationSchema:
    return await service.search_location_by_part_word(name_search)


# --------------- Эндпоинты стран --------------
@router.get(
    "/countries",
    summary="Получить список стран (c основной или детальной информацией)",
    description="Можно получить список стран с базовой информацией, или только список стран для фильтрации",
)
async def get_all_counties(
    only_list: bool = Query(default=False, title="Вернуть только список стран"),
    service: LocationService = Depends(),
) -> Union[list[CountryListSchema], list[CountryDetailSchema]]:
    return await service.get_countries(only_list)


@router.get(
    "/country/id/{country_id}",
    summary="Получить информацию о стране по id",
    description="Получаем подробную базовую информацию о стране",
)
async def get_country_by_id(
    country_id: int = Path(gt=1, title="ID страны"),
    service: LocationService = Depends(),
):
    return await service.get_country(id=country_id)


@router.get(
    "/country/name/{county_name}",
    summary="Получить информацию о стране по названию ENG",
    description="Получаем подробную базовую информацию о стране",
)
async def get_country_by_name(
    county_name: str = Path(title="Название страны"),
    service: LocationService = Depends(),
):
    return await service.get_country(name=county_name)


# --------------- Эндпоинты городов --------------
@router.get(
    "/cities",
    summary="Получить список городов",
    description="Можно получить список городов с базовой информацией, или только список стран для фильтрации",
)
async def get_all_city(
    only_list: bool = Query(default=False, title="Определяет необходимость предоставления базовой информации"),
    service: LocationService = Depends(),
) -> Union[list[LocationOnlyListSchema], list[CityDetailSchema]]:
    return await service.get_cities(only_list)


@router.get(
    "/city/id/{city_id}",
    summary="Получить информацию о городе по id",
    description="Получаем подробную базовую информацию о городе",
)
async def get_city_by_id(
    city_id: int = Path(title="ID города"),
    service: LocationService = Depends(),
):
    return await service.get_city(id=city_id)


@router.get(
    "/city/name/{county_name}_{city_name}",
    summary="Получить информацию о городе по названию страны ENG и города ENG",
    description="Получаем подробную базовую информацию о городе",
)
async def get_city_by_country_id_and_eng(
    county_name: str = Path(title="Название страны"),
    city_name: str = Path(title="Название города"),
    service: LocationService = Depends(),
):
    return await service.get_city(county_name=county_name, city_name=city_name)


@router.get(
    "/city/coordinates/{coordinates}",
    summary="Получить информацию о городе по координатам",
    description="Получаем подробную базовую информацию о городе",
)
async def get_city_by_coordinates(
    coordinates: str = Path(title="Координаты города"),
    service: LocationService = Depends(),
):
    return await service.get_city(coordinates=coordinates)
