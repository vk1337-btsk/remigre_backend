from typing import Union

from fastapi import APIRouter, Body, Depends, Path, Query

from src.ms_metric.schemas import (
    Body_GetLocationsByFilters,
    GetGraphics_Body,
    MetricDetailSchema,
    MetricOnlyListSchema,
)
from src.ms_metric.services import MetricService


router = APIRouter(prefix="/metrics", tags=["Metrics"],include_in_schema=False)


@router.get(
    "",
    summary="Получить список метрик",
    description="Можно получить список метрик с базовой информацией, или только список slug метрик",
)
async def get_all_metrics(
    only_list: bool = Query(default=False, title="Определяет необходимость предоставления базовой информации"),
    service: MetricService = Depends(),
) -> Union[list[MetricOnlyListSchema], list[MetricDetailSchema]]:
    return await service.get_all_metrics(only_list)


@router.get(
    "/metric/{metric_id}",
    summary="Получить информацию о метрике",
    description="Получаем подробную базовую информацию о метрике",
)
async def get_metric(
    metric_id: int = Path(title="ID метрики"),
    service: MetricService = Depends(),
) -> MetricDetailSchema:
    return await service.get_metric(metric_id)


@router.get(
    "/country/{country_id}",
    summary="Получить список всех доступных метрик о стране по её id",
    description="Получаем подробную информацию всех метрик по стране",
)
async def get_all_metrics_country_by_id(
    country_id: int = Path(gt=1, title="ID страны"),
    service: MetricService = Depends(),
):
    return await service.get_all_metrics_for_country(country_id=country_id)


# @router.get(
#     "/city/{city_id}",
#     summary="Получить список всех доступных метрик о стране по её id",
#     description="Получаем подробную информацию всех метрик по стране",
# )
# async def get_all_metrics_city_by_id(
#     city_id: int = Path(gt=1, title="ID страны"),
#     service: MetricService = Depends(),
# ):
#     return await service.get_all_metrics_for_city(city_id=city_id)


# @router.get(
#     "/filters/info",
#     summary="Получает информацию о критериях фильтров",
#     description="Получает информацию о критериях фильтров",
# )
# async def get_filters_info(
#     service: MetricService = Depends(),
# ):
#     return await service.get_filters_info()


@router.post(
    "/filters",
    summary="Получить страны и города по фильтрам метрик",
    description="Получаем список городов и стран по фильтрам метрик",
)
async def get_county_and_city_by_filter(
    body: Body_GetLocationsByFilters = Body(),
    service: MetricService = Depends(),
):
    return await service.get_county_and_city_by_filter(body)


# @router.get(
#     "/city/{city_id}",
#     summary="НЕ РЕАЛИЗОВАНО. Получить список всех доступных метрик о городе по её id",
#     description="Получаем подробную информацию всех метрик по городу",
#     deprecated=True,
# )
# async def get_all_metrics_city_by_id(city_id: int = Path(title="ID города")):
#     pass


# --------------- Эндпоинты графиков --------------
# @router.post(
#     "/country/graphs",
#     summary="НЕ РЕАЛИЗОВАНО. Получить данные метрик о городе по названию страны и города",
#     description="Получаем подробную информацию всех метрик по городу",
#     deprecated=True,
# )
# async def get_graphs(
#     body: GetGraphics_Body = Body(title="Название страны"),
#     county_name: str = Path(title="Название страны"),
#     city_name: str = Path(title="Название города"),
# ):
#     pass
