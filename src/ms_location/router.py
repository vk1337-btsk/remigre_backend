from typing import Optional

from fastapi import APIRouter, Body, Depends, Path, Query

from src.ms_location.schemas import (
    Body_GetCLocationByCoordinates,
    Responce_CityShortInfo,
    Responce_ListPaginatedCountryShortInfo,
    Responce_LocationMainInfoSchema,
    Responce_LocationsGeoJSON,
)
from src.ms_location.services.service import LocationService


router = APIRouter(prefix="/location")


# --------------- Эндпоинты общих действий  --------------
@router.get(
    "/search",
    summary="Поиск стран/городов по названию",
    description=str(
        "Использовать для строк поиска, возвращает список стран/городов по из названию или части названия.\n"
        "Начинаешь вводить название города страны (на русском языке)"
        "(можно делать запрос от 1-го символа) -> получаешь список из вариантов"
    ),
    tags=["Локации - Общее"],
)
async def get_search(
    name: str = Query(min_length=1, title="Название и/или часть названия страны/города"),
    service: LocationService = Depends(),
) -> list[Responce_LocationMainInfoSchema]:

    return await service.search_location_by_part_word(name)


@router.post(
    "/search/map",
    summary="Поиск стран/городов по координатам",
    description=" Возвращает объект страну или города по его координатам",
    tags=["Локации - Общее"],
)
async def get_city_by_coordinates(
    body: Body_GetCLocationByCoordinates = Body(),
    service: LocationService = Depends(),
) -> Responce_LocationMainInfoSchema:

    return await service.get_location_by_coordinates_from_map(body)


@router.get(
    "/map",
    summary="Возвращает координаты стран и городов для карты с основными характеристиками",
    description=str(
        "Использовать для отображения границ стран и точек-городов на карте. "
        "Возвращает координаты стран и городов с основными характеристиками с поддержкой точности отображения координат."
    ),
    tags=["Локации - Общее"],
    response_model=Responce_LocationsGeoJSON,
    responses={200: {"description": "GeoJSON FeatureCollection"}},
)
async def get_coordinates_for_map(
    tolerance: Optional[float] = Query(default=None, title="Точность отображения координат"),
    service: LocationService = Depends(),
):

    return await service.get_coordinates_locations_for_map(tolerance)


# --------------- Эндпоинты стран и городов --------------
@router.get(
    "/countries",
    summary="Получить список стран с основной информацией об их характеристиках и актуальных метриках (с пагинацией)",
    description="Возвращает объект с общим количеством стран и массивом данных для текущей страницы",
    tags=["Локации - Города и Страны"],
    response_model=Responce_ListPaginatedCountryShortInfo,
)
async def get_all_counties(
    service: LocationService = Depends(),
    page: int = Query(default=1, ge=1, description="Номер страницы (начиная с 1)"),
    size: int = Query(default=10, ge=1, le=100, description="Количество записей на странице"),
) -> Responce_ListPaginatedCountryShortInfo:

    return await service.get_list_countries(page=page, size=size)


@router.get(
    "/country/{country_id}",
    summary="Получить информацию о стране по id",
    description="Получаем подробную базовую информацию о стране",
    tags=["Локации - Города и Страны"],
    deprecated=True,
)
async def get_country_by_id(
    country_id: int = Path(gt=1, title="ID страны"),
    service: LocationService = Depends(),
):
    pass


@router.get(
    "/country/{country_id}/cities/short",
    summary="Получить список городов страны по ID",
    description="Можно получить список городов с базовой информацией, или только список стран для фильтрации",
    tags=["Локации - Города и Страны"],
)
async def get_all_city(
    country_id: int = Path(),
    service: LocationService = Depends(),
) -> list[Responce_CityShortInfo]:
    return await service.get_cities_by_country(country_id)


@router.get(
    "/city/{city_id}",
    summary="Получить информацию о городе по id",
    description="Получаем подробную базовую информацию о городе",
    tags=["Локации - Города и Страны"],
    deprecated=True,
)
async def get_city_by_id(
    city_id: int = Path(title="ID города"),
    service: LocationService = Depends(),
):
    pass
