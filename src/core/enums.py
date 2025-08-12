from enum import Enum


class TypeDataEnum(Enum):
    """Типы данных метрик."""

    INT = "int"
    STRING = "string"
    FLOAT = "float"
    RANGE = "range"
    BOOL = "bool"


class PeriodTypeEnum(Enum):
    """Временой промежуток за который делается метрика."""

    ONE_TIME = "one_time"  # Единожды
    YEARLY = "yearly"  # Ежегодно
    MONTHLY = "monthly"  # Ежемесячно
    WEEKLY = "weekly"  # Еженедельно
    INTERVAL = "interval"  # Неопределённый интервал
    NONE = "none"  # Без интервала


class CategoryMetricEnum(Enum):

    ECONOMY = "economy"
    SECURITY = "security"
    QUALITY_OF_LIFE = "quality of life"
    EMIGRATION = "emigration"
    UNCATEGORIZED = "uncategorized"
