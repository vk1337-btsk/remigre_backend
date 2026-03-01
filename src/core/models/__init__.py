from sqlalchemy.orm import configure_mappers

from .locations import CityModel, CountryModel, RegionModel
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
from .others import InfoModel


__all__ = [
    "CountryModel",
    "CityModel",
    "RegionModel",
    "MetricAttributeTypeModel",
    "MetricAttributeValueModel",
    "MetricDataModel",
    "MetricSeriesModel",
    "MetricInfoModel",
    "InfoModel",
    "MetricPeriodModel",
    "MetricSeriesAttribute",
    "MetricPresetModel",
]

configure_mappers()  # Явно конфигурируем все мапперы после импорта всех моделей
