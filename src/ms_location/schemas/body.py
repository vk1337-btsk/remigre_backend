from typing import Literal
from pydantic import Field

from src.core.schemas.base_schemas import BaseSchema


class Body_GetCountryOrCityByCoordinates(BaseSchema):

    type: Literal["city", "country"]
    latitude: float
    longitude: float
