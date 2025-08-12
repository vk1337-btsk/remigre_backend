import logging
from typing import Optional

from pydantic import BaseModel


logger = logging.getLogger(__name__)


class CityOptionsDTO(BaseModel):
    """DTO для подгрузки связей"""

    with_country: bool = False
    with_region: bool = False
    with_data: bool = False


class CityGetDTO(BaseModel):
    """DTO для получения объекта из БД."""

    id: Optional[int] = None
    country_id: Optional[int] = None
    name: Optional[str] = None
    name_eng: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class CityCreateDTO(BaseModel):
    """DTO для создания объекта в БД."""

    country_id: int
    region_id: Optional[int] = None
    name: str
    name_eng: str
    latitude: float
    longitude: float
    is_capital: Optional[bool] = None
    timezone: Optional[str] = None
    population: Optional[int] = None
    language: Optional[str] = None
    climate: Optional[str] = None
    description: Optional[str] = None


class CityUpdateDTO(BaseModel):
    """DTO для изменения объекта в БД."""

    country_id: Optional[int] = None
    region_id: Optional[int] = None
    name: Optional[str] = None
    name_eng: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_capital: Optional[bool] = None
    timezone: Optional[str] = None
    population: Optional[int] = None
    language: Optional[str] = None
    climate: Optional[str] = None
    description: Optional[str] = None
