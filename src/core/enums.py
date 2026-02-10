from enum import Enum


class GeographyLevelEnum(str, Enum):

    COUNTRY = "country"
    CITY = "city"


class TypeDataEnum(str, Enum):
    """Типы данных метрик."""

    STRING = "string"
    FLOAT = "float"
    RANGE = "range"
    BOOL = "bool"


class AttributeTypeValueEnum(str, Enum):
    """Типы атрибутов метрик."""

    STRING = "string"
    CURRENCY = "currency"


class PeriodTypeEnum(str, Enum):
    """Временой промежуток за который делается метрика."""

    ONE_TIME = "one_time"  # Единожды
    YEARLY = "yearly"  # Ежегодно
    MONTHLY = "monthly"  # Ежемесячно
    WEEKLY = "weekly"  # Еженедельно
    INTERVAL = "interval"  # Неопределённый интервал
    NONE = "none"  # Без интервала


class CategoryMetricEnum(str, Enum):

    ECONOMY = "Экономика"
    SECURITY = "Безопасность"
    QUALITY_OF_LIFE = "Качество жизни"
    EMIGRATION = "Эмиграция"
    UNCATEGORIZED = "Без категории"  # Без категории
