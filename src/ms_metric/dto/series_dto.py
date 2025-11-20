# src/ms_metric/dto/series_dto.py
from typing import Optional, Any
from pydantic import BaseModel


class MetricSeriesOptionsDTO(BaseModel):
    """DTO для подгрузки связей серии"""

    with_metric: bool = False
    with_periods: bool = False
    with_data: bool = False


class MetricSeriesGetDTO(BaseModel):
    """DTO для получения серии"""

    id: Optional[int] = None
    metric_id: Optional[int] = None


class MetricSeriesCreateDTO(BaseModel):
    """DTO для создания серии"""

    metric_id: int
    is_active: Optional[bool] = True
    add_info: Optional[dict[str, Any]] = None


class MetricSeriesUpdateDTO(BaseModel):
    """DTO для обновления серии"""

    is_active: Optional[bool] = None
    add_info: Optional[dict[str, Any]] = None
