from typing import Any, List, Literal

from src.core.schemas.base_schemas import BaseSchema


# ============ Схемы для карты ============
class PropertiesCities(BaseSchema):
    """Характеристики города"""

    id: int
    name: str
    is_capital: bool


class PropertiesCountries(BaseSchema):
    """Характеристики страны"""

    id: int
    name: str


class GeoJSONGeometry(BaseSchema):
    """Геометрия объекта карты"""

    type: str
    coordinates: Any


class CountriesGeoJSONFeature(BaseSchema):
    """GeoJSON страны"""

    type: Literal["Feature"]
    geometry: GeoJSONGeometry
    properties: PropertiesCountries


class CitiesGeoJSONFeature(BaseSchema):
    """GeoJSON города"""

    type: Literal["Feature"]
    geometry: GeoJSONGeometry
    properties: PropertiesCities


class CitiesGeoJSONFeatureCollection(BaseSchema):
    """Список GeoJSON городов"""

    type: Literal["FeatureCollection"]
    features: List[CitiesGeoJSONFeature]


class CountriesGeoJSONFeatureCollection(BaseSchema):
    """Список GeoJSON стран"""

    type: Literal["FeatureCollection"]
    features: List[CountriesGeoJSONFeature]


class LocationsGeoJSON(BaseSchema):
    """Список GeoJSON городов и стран"""

    countries: CountriesGeoJSONFeatureCollection
    cities: CitiesGeoJSONFeatureCollection
