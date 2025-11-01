from typing import Optional

from pydantic import Field

from src.core.schemas.base_schemas import BaseSchema
from src.ms_metric.enums import CategoryMetricEnum, TypeDataEnum


class MetricOnlyListSchema(BaseSchema):

    id: int
    slug: str
    name: str


class MetricDetailSchema(BaseSchema):

    id: int
    slug: str
    name: str
    description: Optional[str]
    category: CategoryMetricEnum
    source_name: Optional[str]
    source_url: Optional[str]
    type_data: TypeDataEnum
    unit_format: str
    is_active: bool
