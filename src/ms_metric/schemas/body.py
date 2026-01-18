from datetime import date

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
