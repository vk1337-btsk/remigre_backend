import logging
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from src.core.enums import PeriodTypeEnum


logger = logging.getLogger(__name__)


class MetricPeriodOptionsDTO(BaseModel):
    """DTO для подгрузки связей периода"""

    with_series: bool = False
    with_data: bool = False


class MetricPeriodGetDTO(BaseModel):
    """DTO для получения периода"""

    id: Optional[int] = None
    series_id: Optional[int] = None
    period_type: Optional[PeriodTypeEnum] = None
    period_year: Optional[int] = None
    period_month: Optional[int] = None
    period_week: Optional[int] = None


class MetricPeriodCreateDTO(BaseModel):
    """DTO для создания периода"""

    series_id: int
    period_type: PeriodTypeEnum
    period_year: Optional[int] = None
    period_month: Optional[int] = None
    period_week: Optional[int] = None
    date_start: Optional[datetime] = None
    date_end: Optional[datetime] = None
    collected_at: Optional[datetime] = None
    add_info: Optional[dict[str, Any]] = None


class MetricPeriodUpdateDTO(BaseModel):
    """DTO для обновления периода"""

    period_type: Optional[PeriodTypeEnum] = None
    period_year: Optional[int] = None
    period_month: Optional[int] = None
    period_week: Optional[int] = None
    date_start: Optional[datetime] = None
    date_end: Optional[datetime] = None
    collected_at: Optional[datetime] = None
    add_info: Optional[dict[str, Any]] = None
