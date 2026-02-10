from sqlalchemy.orm import configure_mappers

from .attribute_type import MetricAttributeTypeModel
from .attribute_value import MetricAttributeValueModel
from .data import MetricDataNewModel
from .info import MetricInfoNewModel
from .period import MetricPeriodNewModel
from .series import MetricSeriesNewModel
from .series_attributes import MetricSeriesAttribute


configure_mappers()  # Явно конфигурируем все мапперы после импорта всех моделей


__all__ = [
    "MetricAttributeTypeModel",
    "MetricAttributeValueModel",
    "MetricDataNewModel",
    "MetricInfoNewModel",
    "MetricPeriodNewModel",
    "MetricSeriesNewModel",
    "MetricSeriesAttribute",
]
