import logging
from typing import Optional

from pydantic import BaseModel, model_validator


logger = logging.getLogger(__name__)


class CountryOptionsDTO(BaseModel):
    """DTO для подгрузки связей"""

    with_region: bool = False
    with_city: bool = False
    with_data: bool = False


class CountryGetDTO(BaseModel):
    """DTO для получения объекта из БД."""

    id: Optional[int] = None
    name: Optional[str] = None
    name_eng: Optional[str] = None
    iso_code: Optional[str] = None


class CountryCreateDTO(BaseModel):
    """DTO для создания объекта в БД."""

    name: str
    name_eng: str
    iso_code: str
    latitude: float
    longitude: float
    language: Optional[str] = None
    currency: Optional[str] = None
    timezone: Optional[str] = None
    migration_policy: Optional[str] = None
    description: Optional[str] = None
    population: Optional[int] = None
    climate: Optional[str] = None
    is_active: Optional[bool] = True


class CountryUpdateDTO(BaseModel):
    """DTO для изменения объекта в БД."""

    name: Optional[str] = None
    name_eng: Optional[str] = None
    iso_code: Optional[str] = None
    latitude: Optional[float]
    longitude: Optional[float]
    language: Optional[str] = None
    currency: Optional[str] = None
    timezone: Optional[str] = None
    migration_policy: Optional[str] = None
    description: Optional[str] = None
    population: Optional[int] = None
    climate: Optional[str] = None
    is_active: Optional[bool] = None
