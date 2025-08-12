#
from src.ms_location.models.city import CityModel
from src.ms_location.models.country import CountryModel
from src.ms_location.models.region import RegionModel

#
from src.ms_main.models.info import InfoModel

#
from src.ms_metric.models.data import MetricDataModel
from src.ms_metric.models.metric import MetricModel
from src.ms_metric.models.period import MetricPeriodModel


# Здесь ничего не нужно делать — просто импортируем, чтобы SQLAlchemy успел зарегистрировать их мапперы
# Можно добавить __all__ если хочешь автокомплита
__all__ = [
    "CountryModel",
    "CityModel",
    "RegionModel",
    "MetricDataModel",
    "MetricModel",
    "MetricPeriodModel",
    "InfoModel",
]
