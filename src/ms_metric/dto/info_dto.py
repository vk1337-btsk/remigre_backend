# src/ms_metric/dto/info_dto.py (или в существующий metric_dto.py, но с новыми именами)

from typing import Any, Optional

from pydantic import BaseModel

from src.ms_metric.enums import CategoryMetricEnum, TypeDataEnum


class MetricInfoOptionsDTO(BaseModel):
    """DTO для подгрузки связей индикатора"""

    with_series: bool = False
    with_period: bool = False
    with_data: bool = False


class MetricInfoGetDTO(BaseModel):
    """DTO для получения индикатора"""

    id: Optional[int] = None
    slug: Optional[str] = None


class MetricInfoCreateDTO(BaseModel):
    """DTO для создания индикатора"""

    slug: str
    name: str
    description: Optional[str] = None
    category: CategoryMetricEnum
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    type_data: TypeDataEnum
    is_active: Optional[bool] = True
    add_info: Optional[dict[str, Any]] = None


class MetricInfoUpdateDTO(BaseModel):
    """DTO для обновления индикатора"""

    slug: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[CategoryMetricEnum] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    type_data: Optional[TypeDataEnum] = None
    is_active: Optional[bool] = None
    add_info: Optional[dict[str, Any]] = None
