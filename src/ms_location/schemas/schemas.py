from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator
from shapely.geometry import mapping
from shapely.wkb import loads

from src.core.enums import TypeDataEnum
from src.core.models import CountryModel
from src.core.schemas.base_schemas import BaseSchema


class LocationMainInfoSchema(BaseSchema):
    """Список стран/городов"""

    id: int = Field(title="ID объекта локации")
    type: Literal["country", "city"] = Field(title="Тип объекта локации (страна или город)")
    name: str = Field(title="Название объекта локации (на русском)")
    iso_code: str = Field(title="ISO-code alpha 2 страны объекта локации")


# ============ Схемы для стран ============
class ShortMetricValueDTO(BaseModel):

    value_numeric: Optional[float] = Field(default=None)
    value_string: Optional[str] = Field(default=None)
    value_boolean: Optional[bool] = Field(default=None)
    value_range_start: Optional[float] = Field(default=None)
    value_range_end: Optional[float] = Field(default=None)
    year: int
    attributes: Dict[str, List[str]]


class ShortMetricInfoDTO(BaseModel):

    id: int
    name: str
    type: TypeDataEnum
    display_priority: int
    values: List[ShortMetricValueDTO]


class MetricValueSchema(BaseModel):

    value: Any
    year: int
    priority: int
    attributes: Dict[str, str]


class MetricInfoSchema(BaseModel):
    id: int
    name: str
    type: TypeDataEnum
    values: List[MetricValueSchema]


class CountryShortInfoDetail(BaseModel):
    """Информация о стране"""

    id: int
    name: str
    iso_alpha_2: str
    population: Optional[int]
    metrics: List[MetricInfoSchema] = Field(default_factory=list)


class ListPaginatedCountryShortInfo(BaseModel):

    total: int = Field(default=0)
    items: List[CountryShortInfoDetail] = Field(default_factory=list)


# ============
class LocationOnlyListSchema(BaseSchema):

    id: int
    country_id: Optional[int] = Field(default=None)
    name: str


class CountryListSchema(BaseSchema):

    id: int
    name: str


class CountryDetailSchema(BaseSchema):

    id: int
    name: str
    name_eng: str
    iso_alpha_2: str
    iso_alpha_3: str
    iso_digits: Optional[str] = None
    latitude: float
    longitude: float
    geometry: Optional[dict]
    language: Optional[str]
    currency: Optional[str]
    timezone: Optional[str]
    migration_policy: Optional[str]
    description: Optional[str]
    population: Optional[int]
    climate: Optional[str]

    model_config = {"from_attributes": True}

    @field_validator("geometry")
    @classmethod
    def validate_geometry(cls, v):
        if v is not None and not isinstance(v, dict):
            raise ValueError("geometry must be a dict (GeoJSON)")
        return v

    @classmethod
    def from_orm_with_geojson(cls, country_model: "CountryModel") -> "CountryDetailSchema":
        geo_dict = None
        if country_model.geometry is not None:
            geo_shape = loads(bytes(country_model.geometry.data))  # WKB -> shapely
            geo_dict = mapping(geo_shape)  # shapely -> dict (GeoJSON)

        # Создаём словарь атрибутов для Pydantic
        country_data = {
            **{k: getattr(country_model, k) for k in country_model.__table__.columns.keys() if k != "geometry"},
            "geometry": geo_dict,
        }

        return cls.model_validate(country_data)


class CityDetailSchema(BaseSchema):

    id: int
    country_id: int
    name: str
    name_eng: str
    latitude: float
    longitude: float
    is_capital: bool
    timezone: Optional[str]
    population: Optional[int]
    language: Optional[str]
    climate: Optional[str]
    description: Optional[str]
