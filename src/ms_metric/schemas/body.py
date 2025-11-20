from datetime import date
from src.core.schemas.base_schemas import BaseSchema


class GetGraphics_Body(BaseSchema):

    country_id: int

    slug: str

    date_start: date
    date_end: date

    unit: str
