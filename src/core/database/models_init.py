from src.ms_location.models import CityModel, CountryModel, RegionModel
from src.ms_main.models.info import InfoModel
from src.ms_metric.models import (
    MetricDataModel,
    MetricInfoModel,
    MetricPeriodModel,
    MetricSeriesModel,
)


# Здесь ничего не нужно делать — просто импортируем, чтобы SQLAlchemy успел зарегистрировать их мапперы
# Можно добавить __all__ если хочешь автокомплита
__all__ = [
    "CountryModel",
    "CityModel",
    "RegionModel",
    "MetricDataModel",
    "MetricPeriodModel",
    "MetricSeriesModel",
    "MetricInfoModel",
    "InfoModel",
]
