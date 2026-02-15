# etl/utils/period_key.py
"""
Функция, вычитающая ключ периода
"""
from typing import Union

from etl.config.config_schema import PeriodDataDTO
from src.ms_metric.models import MetricPeriodNewModel


def make_period_key(period: Union[PeriodDataDTO, MetricPeriodNewModel]) -> str:
    """Генерирует строковый ключ периода на основе его полей."""

    if isinstance(period, MetricPeriodNewModel):
        period_type = period.period_type.value if hasattr(period.period_type, "value") else period.period_type
        year = period.period_year
        month = period.period_month
        quarter = period.period_quarter
        week = period.period_week
    else:
        period_type = period.period_type
        year = period.period_year
        month = period.period_month
        quarter = period.period_quarter
        week = period.period_week

    key = f"{period_type}_{year}"
    if month is not None:
        key += f"_{month}"
    if quarter is not None:
        key += f"_q{quarter}"
    if week is not None:
        key += f"_w{week}"
    return key
