from typing import Literal

from pydantic import BaseModel, Field


class Body_GetCLocationByCoordinates(BaseModel):
    """Тело POST запроса для получения страны/города по координатам"""

    type: Literal["city", "country"] = Field(description="Тип локации, которую хотим получить")
    latitude: float = Field(description="Широта локации с карты")
    longitude: float = Field(description="Долгота локации с карты")
