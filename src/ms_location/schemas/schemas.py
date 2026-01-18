from typing import List, Literal, Optional, Tuple, Union

from pydantic import BaseModel, Field, field_validator
from shapely.geometry import mapping
from shapely.wkb import loads

from src.core.schemas.base_schemas import BaseSchema
from src.ms_location.models.country import CountryModel


class LocationOnlyListSchema(BaseSchema):

    id: int
    country_id: Optional[int] = Field(default=None)
    name: str


class CountryListSchema(BaseSchema):

    id: int
    name: str


class SearchLocationSchema(BaseSchema):

    country: list[LocationOnlyListSchema]
    cities: list[LocationOnlyListSchema]


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


# ======================================================================================================================
class CoordinatesSchema(BaseModel):
    """Схема с координатами локаций (стран и городов для карты)"""

    id: int
    name: str
    type: Literal["Point", "Polygon", "MultiPolygon", "Feature"] = Field(
        default="Feature", title="Тип передаваемого GeoJSON"
    )
    coordinates: Union[List[Tuple[float, float]], List[List[Tuple[float, float]]]]


class CoordinatesLocationsForMap(BaseModel):
    """Схема с координатами локаций (стран и городов для карты)"""

    countries: list[CoordinatesSchema]
    cities: list[CoordinatesSchema]
