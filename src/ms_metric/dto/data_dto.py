import logging
from typing import Any, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class MetricDataOptionsDTO(BaseModel):
    """DTO для подгрузки связей"""

    with_series: bool = False
    with_period: bool = False
    with_country: bool = False
    with_city: bool = False


class MetricDataGetDTO(BaseModel):
    """DTO для получения записи данных"""

    id: Optional[int] = None
    series_id: Optional[int] = None
    period_id: Optional[int] = None
    country_id: Optional[int] = None
    city_id: Optional[int] = None


class MetricDataCreateDTO(BaseModel):
    """DTO для создания данных метрики"""

    series_id: int
    period_id: int
    country_id: Optional[int] = None
    city_id: Optional[int] = None
    value_int: Optional[int] = None
    value_string: Optional[str] = None
    value_float: Optional[float] = None
    value_range_min: Optional[float] = None
    value_range_max: Optional[float] = None
    value_bool: Optional[bool] = None
    add_info: Optional[dict[str, Any]] = None


class MetricDataUpdateDTO(BaseModel):
    """DTO для обновления данных метрики"""

    value_int: Optional[int] = None
    value_string: Optional[str] = None
    value_float: Optional[float] = None
    value_range_min: Optional[float] = None
    value_range_max: Optional[float] = None
    value_bool: Optional[bool] = None
    add_info: Optional[dict[str, Any]] = None
