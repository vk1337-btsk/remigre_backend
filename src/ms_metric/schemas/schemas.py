from typing import Any, Optional

from pydantic import Field

from src.core.schemas.base_schemas import BaseSchema
from src.ms_metric.enums import (
    CategoryMetricEnum,
    FiltredMetricGenderEnum,
    TypeDataEnum,
)


class MetricOnlyListSchema(BaseSchema):

    id: int
    slug: str
    name: str
    description: Optional[str]


class MetricDetailSchema(BaseSchema):

    id: int
    slug: str
    name: str
    description: Optional[str]
    category: CategoryMetricEnum
    source_name: Optional[str]
    source_url: Optional[str]
    type_data: TypeDataEnum
    is_active: bool

    add_info: Any  # dict[str, list[str]]


class FiltersInfo(BaseSchema):

    category: list[str]
    gender: list[str]


class FilteredLocation(BaseSchema):

    id: int


class GetFilteredListLocations(BaseSchema):

    countries: list
    cities: list
