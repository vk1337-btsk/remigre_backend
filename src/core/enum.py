from enum import Enum


class TypeDataEnum(Enum):
    """Типы данных метрик."""

    STR = "str"
    INT = "int"
    FLOAT = "float"
    RANGE = "range"


class TypeCategoryEnum(Enum):
    """Объект к которому относится метрика: страна, город или оба."""

    COUNTRY = "country"
    CITY = "city"
    COUNTRY_AND_CITY = "country and city"


class PeriodTypeEnum(Enum):
    """Временой промежуток за который делается метрика."""

    ONE_TIME = "one_time"
    YEARLY = "yearly"
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    INTERVAL = "interval"
    NONE = "none"
