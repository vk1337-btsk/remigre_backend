import logging
from typing import Union

from fastapi import APIRouter, Body, Depends, Path, Query

from src.ms_location.schemas import (
    Body_GetCountryOrCityByCoordinates,
    CityDetailSchema,
    CoordinatesLocationsForMap,
    CountryDetailSchema,
    CountryListSchema,
    LocationOnlyListSchema,
    SearchLocationSchema,
)
from src.ms_location.services.location_service import LocationService


logger = logging.getLogger(__name__)


router = APIRouter(prefix="/location")


# --------------- Эндпоинты общих действий  --------------
@router.get(
    "/search",
    summary="Поиск по названию страны/города",
    description="Начинаешь вводить название -> получаешь варианты",
    tags=["Локации - Общее"],
)
async def get_search(
    name_search: str = Query(min_length=3, title="Название и/или часть названия страны/города"),
    service: LocationService = Depends(),
) -> SearchLocationSchema:
    return await service.search_location_by_part_word(name_search)


@router.get(
    "/map",
    summary="Возвращает координаты стран и городов для карты",
    description="Возвращает координаты стран и городов для карты",
    tags=["Локации - Общее"],
)
async def get_coordinates_for_map(
    service: LocationService = Depends(),
) -> CoordinatesLocationsForMap:
    return await service.get_coordinates_for_map()


@router.post(
    "/map",
    summary="Получить ID страны или города по его координатам",
    description="Получаем ID страны или города по его координатам",
    tags=["Локации - Общее"],
)
async def get_city_by_coordinates(
    body: Body_GetCountryOrCityByCoordinates = Body(),
    service: LocationService = Depends(),
) -> int:
    return await service.get_id_country_or_city_by_coordinates(body)


# --------------- Эндпоинты стран и городов --------------
@router.get(
    "/countries",
    summary="Получить список стран (c основной или детальной информацией)",
    description="Можно получить список стран с базовой информацией, или только список стран для фильтрации",
    tags=["Локации - Города и Страны"],
)
async def get_all_counties(
    only_list: bool = Query(default=False, title="Вернуть только список стран"),
    service: LocationService = Depends(),
) -> Union[list[CountryListSchema], list[CountryDetailSchema]]:
    return await service.get_countries(only_list)


@router.get(
    "/country/{country_id}",
    summary="Получить информацию о стране по id",
    description="Получаем подробную базовую информацию о стране",
    tags=["Локации - Города и Страны"],
)
async def get_country_by_id(
    country_id: int = Path(gt=1, title="ID страны"),
    service: LocationService = Depends(),
):
    return await service.get_country(id=country_id)


@router.get(
    "/cities",
    summary="Получить список городов",
    description="Можно получить список городов с базовой информацией, или только список стран для фильтрации",
    tags=["Локации - Города и Страны"],
)
async def get_all_city(
    only_list: bool = Query(default=False, title="Определяет необходимость предоставления базовой информации"),
    service: LocationService = Depends(),
) -> Union[list[LocationOnlyListSchema], list[CityDetailSchema]]:
    return await service.get_cities(only_list)


@router.get(
    "/city/{city_id}",
    summary="Получить информацию о городе по id",
    description="Получаем подробную базовую информацию о городе",
    tags=["Локации - Города и Страны"],
)
async def get_city_by_id(
    city_id: int = Path(title="ID города"),
    service: LocationService = Depends(),
):
    return await service.get_city(id=city_id)
