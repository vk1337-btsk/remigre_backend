from datetime import date, datetime
from typing import Literal, Optional

from src.core.schemas.base_schemas import BaseSchema
from src.ms_metric.enums import FiltredMetricGenderEnum


class GetGraphics_Body(BaseSchema):
    """Тело для получения графиков по странам"""

    country_id: int
    city_id: int

    slug: str

    date_from: date
    date_to: date

    unit: str

    gender: FiltredMetricGenderEnum


class MetricFilters(BaseSchema):

    metric_id: int
    filters: dict[str, list[str]]

    value_from: Optional[datetime]
    value_to: Optional[datetime]

    date_from: Optional[datetime]
    date_to: Optional[datetime]


class Body_GetLocationsByFilters(BaseSchema):

    type: Literal["all", "country", "city"]

    metrics: list[MetricFilters]
