from typing import Union

from fastapi import APIRouter, Depends, Path, Query

from src.ms_metric.schemas import MetricDetailSchema, MetricOnlyListSchema
from src.ms_metric.services import MetricService


router = APIRouter(prefix="/metrics", tags=["Metrics"])


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
    "/{slug}",
    summary="Получить информацию о метрике",
    description="Получаем подробную базовую информацию о метрике",
)
async def get_metric(
    slug: str = Path(title="slug метрики"),
    service: MetricService = Depends(),
) -> MetricDetailSchema:
    return await service.get_metric(slug)


@router.get(
    "/filters",
    summary="Получить страны и города по фильтрам метрик",
    description="Получаем список городов и стран по фильтрам метрик",
    deprecated=True,
)
async def get_county_and_city_by_filter(
    only_list: bool = Query(default=False, title="Определяет необходимость предоставления базовой информации"),
    population: int = Query(title="Как пример"),
    language: str = Query(title="Как пример"),
    currency: str = Query(title="Как пример"),
    min_salary: int = Query(title="Как пример"),
    max_salary: int = Query(title="Как пример"),
):
    pass


@router.get(
    "/country/{country_id}",
    summary="Получить данные метрик о стране по id",
    description="Получаем подробную информацию всех метрик по стране",
)
async def get_all_metrics_country_by_id(
    country_id: int = Path(gt=1, title="ID страны"),
    service: MetricService = Depends(),
):
    return await service.get_all_metrics_for_country(country_id=country_id)


@router.get(
    "/country/{country_name}",
    summary="Получить данные метрик о стране по названию",
    description="Получаем подробную информацию всех метрик по стране",
)
async def get_all_metrics_country_by_name(
    country_name: str = Path(title="Название страны"),
    service: MetricService = Depends(),
):
    return await service.get_all_metrics_for_country(country_name=country_name)


@router.get(
    "/city/{city_id}",
    summary="Получить данные метрик о стране по id",
    description="Получаем подробную информацию всех метрик по городу",
    deprecated=True,
)
async def get_all_metrics_city_by_id(city_id: int = Path(title="ID города")):
    pass


@router.get(
    "/city/{country_name}_{city_name}",
    summary="Получить данные метрик о городе по названию страны и города",
    description="Получаем подробную информацию всех метрик по городу",
    deprecated=True
)
async def get_all_metrics_city_by_name(
    county_name: str = Path(title="Название страны"),
    city_name: str = Path(title="Название города"),
):
    pass
