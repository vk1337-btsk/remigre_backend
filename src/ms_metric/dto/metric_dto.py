import logging
from typing import Optional

from pydantic import BaseModel

from src.ms_metric.enums import CategoryMetricEnum, TypeDataEnum


logger = logging.getLogger(__name__)


class MetricOptionsDTO(BaseModel):
    """DTO для подгрузки связей"""

    with_period: bool = False
    with_data: bool = False


class MetricGetDTO(BaseModel):
    """DTO для получения объекта из БД."""

    id: Optional[int] = None
    slug: Optional[str] = None


class MetricCreateDTO(BaseModel):
    """DTO для создания объекта в БД."""

    slug: str
    name: str
    description: Optional[str] = None
    category: CategoryMetricEnum
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    type_data: TypeDataEnum
    unit_format: str
    is_active: Optional[bool] = None


class MetricUpdateDTO(BaseModel):
    """DTO для изменения объекта в БД."""

    slug: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[CategoryMetricEnum] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    type_data: Optional[TypeDataEnum] = None
    unit_format: Optional[str] = None
    is_active: Optional[bool] = None
