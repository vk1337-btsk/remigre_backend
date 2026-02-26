import logging
from typing import Optional, Union

from fastapi import APIRouter, Body, Depends, Path, Query

from src.ms_location.schemas import (
    Body_GetCountryOrCityByCoordinates,
    CityDetailSchema,
    LocationMainInfoSchema,
    LocationOnlyListSchema,
    LocationsGeoJSON,
)
from src.ms_location.schemas.schemas import (
    CountryShortInfoDetail,
    ListPaginatedCountryShortInfo,
)
from src.ms_location.services.service import LocationService


logger = logging.getLogger(__name__)


router = APIRouter(prefix="/location")


# --------------- Эндпоинты общих действий  --------------
@router.get(
    "/search",
    summary="РЕАЛИЗОВАНО: Поиск стран/городов по названию",
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
) -> list[LocationMainInfoSchema]:

    return await service.search_location_by_part_word(name)


@router.post(
    "/search/map",
    summary="РЕАЛИЗОВАНО: Поиск стран/городов по координатам",
    description=" Возвращает объект страну или города по его координатам",
    tags=["Локации - Общее"],
)
async def get_city_by_coordinates(
    body: Body_GetCountryOrCityByCoordinates = Body(),
    service: LocationService = Depends(),
) -> LocationMainInfoSchema:

    return await service.get_location_by_coordinates_from_map(body)


@router.get(
    "/map",
    summary="РЕАЛИЗОВАНО: Возвращает координаты стран и городов для карты с основными характеристиками",
    description=str(
        "Использовать для отображения границ стран и точек-городов на карте. "
        "Возвращает координаты стран и городов с основными характеристиками с поддержкой точности отображения координат."
    ),
    tags=["Локации - Общее"],
    response_model=LocationsGeoJSON,
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
    summary="РЕАЛИЗОВАНО: Получить список стран с основной информацией об их характеристиках и актуальных метриках (с пагинацией)",
    description="Возвращает объект с общим количеством стран и массивом данных для текущей страницы",
    tags=["Локации - Города и Страны"],
    response_model=ListPaginatedCountryShortInfo,
)
async def get_all_counties(
    service: LocationService = Depends(),
    limit: int = Query(10, ge=1, le=100, description="Количество записей на странице"),
    offset: int = Query(0, ge=0, description="Смещение от начала списка"),
) -> ListPaginatedCountryShortInfo:

    return await service.get_list_countries(limit=limit, offset=offset)


# @router.get(
#     "/country/{country_id}",
#     summary="Получить информацию о стране по id",
#     description="Получаем подробную базовую информацию о стране",
#     tags=["Локации - Города и Страны"],
# )
# async def get_country_by_id(
#     country_id: int = Path(gt=1, title="ID страны"),
#     service: LocationService = Depends(),
# ):
#     return await service.get_country(id=country_id)


# @router.get(
#     "/cities",
#     summary="Получить список городов",
#     description="Можно получить список городов с базовой информацией, или только список стран для фильтрации",
#     tags=["Локации - Города и Страны"],
# )
# async def get_all_city(
#     only_list: bool = Query(default=False, title="Определяет необходимость предоставления базовой информации"),
#     service: LocationService = Depends(),
# ) -> Union[list[LocationOnlyListSchema], list[CityDetailSchema]]:
#     return await service.get_cities(only_list)


# @router.get(
#     "/city/{city_id}",
#     summary="Получить информацию о городе по id",
#     description="Получаем подробную базовую информацию о городе",
#     tags=["Локации - Города и Страны"],
# )
# async def get_city_by_id(
#     city_id: int = Path(title="ID города"),
#     service: LocationService = Depends(),
# ):
#     return await service.get_city(id=city_id)
