from sqlalchemy.orm import configure_mappers

from .locations import CityModel, CountryModel
from .metrics import (
    MetricAttributeTypeModel,
    MetricAttributeValueModel,
    MetricDataModel,
    MetricInfoModel,
    MetricPeriodModel,
    MetricPresetModel,
    MetricSeriesAttribute,
    MetricSeriesModel,
)
from .others import ImageModel, InfoModel


__all__ = [
    "CountryModel",
    "CityModel",
    "MetricAttributeTypeModel",
    "MetricAttributeValueModel",
    "MetricDataModel",
    "MetricSeriesModel",
    "MetricInfoModel",
    "InfoModel",
    "MetricPeriodModel",
    "MetricSeriesAttribute",
    "MetricPresetModel",
    "ImageModel",
]

configure_mappers()  # Явно конфигурируем все мапперы после импорта всех моделей
