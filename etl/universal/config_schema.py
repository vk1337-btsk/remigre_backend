# etl/universal/config_schema.py
"""
Схемы конфигурации для универсального ETL
"""
from datetime import date
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.core.enums import (
    AttributeTypeValueEnum,
    CategoryMetricEnum,
    GeographyLevelEnum,
    PeriodTypeEnum,
    TypeDataEnum,
)


# Константы для конфига
DEFAULT_TYPE_IS_ACTIVE = True
DEFAULT_TYPE_IS_FILTERED = False
DEFAULT_TYPE_VALUE_TYPE = AttributeTypeValueEnum.STRING
DEFAULT_TYPE_SORT_ORDER = 0
DEFAULT_TYPE_META_DATA = None

DEFAULT_VALUE_IS_ACTIVE = True
DEFAULT_VALUE_IS_FILTERED = False
DEFAULT_VALUE_SORT_ORDER = 0
DEFAULT_VALUE_META_DATA = None


class FieldSourceTypeEnum(str, Enum):

    COLUMN = "column"  # column (из колонки)
    FIXED = "fixed"  # fixed (фиксированное значение)
    CALLBACK = "callback"  #  callback (кастомная функция)


class AttributeParsingStrategyEnum(str, Enum):
    """Стратегии парсинга атрибутов"""

    FIXED_TYPE = "Код и название атрибута зафиксированы, код и название значения атрибута - из ячйке"
    CUSTOM = "Кастомная функция для получения: кода и названия атрибута, а также кода и названия значения атрибута"
    COMPLEX = "Комплекс: из одной колонки извлекается несколько атрибутов "
    "(кода и название атрибута, код и название значения атрибута), а также данные периода"


class AttributeTypeDTO(BaseModel):
    """DTO для типа атрибута"""

    code: str = Field(max_length=255, description="Уникальный код типа атрибута")
    name: str = Field(max_length=255, description="Название типа атрибута")
    value_type: AttributeTypeValueEnum = Field(
        default=DEFAULT_TYPE_VALUE_TYPE, description="Тип значения: string, number, currency, boolean"
    )
    is_active: bool = Field(default=DEFAULT_TYPE_IS_FILTERED, description="Активен ли тип атрибута")
    is_filtered: bool = Field(default=DEFAULT_TYPE_IS_FILTERED, description="Используется ли для фильтрации")
    sort_order: int = Field(default=DEFAULT_TYPE_SORT_ORDER, description="Порядок сортировки")
    meta_data: Optional[Dict[str, Any]] = Field(default=None, description="Метаданные типа атрибута")


class AttributeValueDTO(BaseModel):
    """DTO для значения атрибута"""

    code: str = Field(max_length=255, description="Код значения атрибута (уникальный в пределах типа)")
    name: str = Field(max_length=255, description="Название значения атрибута")
    is_active: bool = Field(default=DEFAULT_VALUE_IS_ACTIVE, description="Активно ли значение атрибута")
    is_filtered: bool = Field(default=DEFAULT_VALUE_IS_FILTERED, description="Используется ли для фильтрации")
    sort_order: int = Field(default=DEFAULT_VALUE_SORT_ORDER, description="Порядок сортировки")
    meta_data: Optional[Dict[str, Any]] = Field(
        default=DEFAULT_VALUE_META_DATA, description="Метаданные значения атрибута"
    )


class ParsedAttributeDTO(BaseModel):
    """DTO распаршенного атрибута - объединяет тип и значение"""

    type: AttributeTypeDTO = Field(description="Данные типа атрибута")
    value: AttributeValueDTO = Field(description="Данные значения атрибута")


class PeriodDataDTO(BaseModel):
    """DTO данных периода"""

    period_year: Optional[int] = Field(default=None, description="Год периода")
    period_month: Optional[int] = Field(default=None, description="Месяц периода (1-12)", ge=1, le=12)
    period_quarter: Optional[int] = Field(default=None, description="Квартал периода (1-4)", ge=1, le=4)
    period_week: Optional[int] = Field(default=None, description="Неделя периода (1-53)", ge=1, le=53)
    date_start: Optional[date] = Field(default=None, description="Дата начала периода")
    date_end: Optional[date] = Field(default=None, description="Дата окончания периода")
    collected_at: Optional[date] = Field(default=None, description="Дата и время сбора данных")
    meta_data: Optional[Dict[str, Any]] = Field(default=None, description="Метаданные периода")


class ComplexParseResultDTO(BaseModel):
    """Результат комплексного парсинга"""

    attributes: List[ParsedAttributeDTO] = Field(default_factory=list, description="Список распаршенных атрибутов")
    period_data: Optional[PeriodDataDTO] = Field(default=None, description="Данные периода (если извлечены из строки)")


class AttributeConfig(BaseModel):
    """Конфигурация атрибута/фильтра"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # =========== Основные данные
    csv_column: str = Field(description="Название колонки в CSV файле")

    # =========== Стратегия парсинга
    parsing_strategy: AttributeParsingStrategyEnum = Field(description="Стратегия парсинга значения из колонки")

    # Для FIXED_TYPE стратегии
    # metric_attribute_type.code и metric_attribute_type.name = задаётся
    # metric_attribute_value.code и metric_attribute_value.name = значение из ячейки
    attribute_type_code: Optional[str] = Field(
        default=None, description="Фиксированный код типа атрибута (для FIXED_TYPE стратегии)"
    )
    attribute_type_name: Optional[str] = Field(
        default=None, description="Фиксированное название типа атрибута (для FIXED_TYPE стратегии)"
    )

    # Для CUSTOM стратегии
    # можно будет добавить имя функции или callback, чтобы она вернула:
    # metric_attribute_type.code и metric_attribute_type.name
    # metric_attribute_value.code и metric_attribute_value.name
    custom_parser: Optional[Callable[[str], ParsedAttributeDTO]] = Field(
        default=None,
        description="Кастомная функция парсинга. Должна принимать строку и возвращать ParsedAttributeDTO для атрибута",
    )

    # Для COMPLEX стратегии - возвращает несколько атрибутов и данные периода
    complex_parser: Optional[Callable[[str], ComplexParseResultDTO]] = Field(
        default=None,
        description="Комплексная функция парсинга. Должна принимать строку и возвращать атрибуты и "
        "данные периода (ComplexParseResultDTO)",
    )

    # Общие настройки (применяются ко всем типам атрибутам, если не переопределены)
    def_type_value_type: AttributeTypeValueEnum = Field(
        default=DEFAULT_TYPE_VALUE_TYPE, description="Значение типа атрибута по умолчанию для типа атрибута"
    )
    def_type_is_active: bool = Field(
        default=DEFAULT_TYPE_IS_ACTIVE, description="Статус активности по умолчанию для типа атрибута"
    )
    def_type_is_filtered: bool = Field(
        default=DEFAULT_TYPE_IS_FILTERED, description="Статус фильтра по умолчанию для типа атрибута"
    )
    def_type_sort_order: int = Field(
        default=DEFAULT_TYPE_SORT_ORDER,
        description="Значение сортировки по умолчанию для типа атрибута",
    )
    def_type_meta_data: Optional[Dict[str, Any]] = Field(
        default=DEFAULT_TYPE_META_DATA, description="Метаданные по умолчанию для типа атрибутов"
    )
    # Общие настройки (применяются ко всем значениям атрибутов, если не переопределены)
    def_value_is_active: bool = Field(
        default=DEFAULT_VALUE_IS_ACTIVE, description="Значение по умолчанию для значения атрибута"
    )
    def_value_is_filtered: bool = Field(
        default=DEFAULT_VALUE_IS_FILTERED, description="Статус фильтра по умолчанию для значения атрибута"
    )
    def_value_sort_order: int = Field(
        default=DEFAULT_VALUE_SORT_ORDER, description="Значение сортировки по умолчанию для значения атрибута"
    )
    def_value_meta_data: Optional[Dict[str, Any]] = Field(
        default=DEFAULT_VALUE_META_DATA, description="Метаданные по умолчанию для значения атрибутов"
    )

    @model_validator(mode="after")
    def validate_parsing_strategy(self):
        """Валидация стратегии парсинга"""

        if self.parsing_strategy == AttributeParsingStrategyEnum.FIXED_TYPE:
            if not self.attribute_type_code:
                raise ValueError("При parsing_strategy='fixed_type' должен быть задан attribute_type_code")

        if self.parsing_strategy == AttributeParsingStrategyEnum.CUSTOM:
            if not self.custom_parser:
                raise ValueError("При parsing_strategy='custom' должен быть задан custom_parser")

        if self.parsing_strategy == AttributeParsingStrategyEnum.COMPLEX:
            if not self.complex_parser:
                raise ValueError("При parsing_strategy='complex' должен быть задан complex_parser")

        return self


class FieldSourceDTO(BaseModel):
    """Конфигурация источника данных для поля"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Тип источника
    source_type: FieldSourceTypeEnum = Field(
        default=FieldSourceTypeEnum.COLUMN,
        description="Enum для типа источника: из колонки, фиксированное значение, кастомная функция",
    )

    column_name: Optional[str] = Field(
        default=None, description="Название колонки в CSV (используется при source_type='column')"
    )  # Для source_type="column"

    fixed_value: Optional[Any] = Field(
        default=None, description="Фиксированное значение (используется при source_type='fixed')"
    )  # Для source_type="fixed"

    callback: Optional[Callable[[Dict[str, str]], Any]] = Field(
        default=None, description="Кастомная функция, принимающая строку CSV и возвращающая значение"
    )  # Для source_type="callback"

    # Для всех типов
    transform_callback: Optional[Callable[[Any], Any]] = Field(
        default=None, description="Функция для трансформации значения после получения"
    )

    @model_validator(mode="after")
    def validate_source_type(self):
        """Валидация типа источника"""

        if self.source_type == FieldSourceTypeEnum.COLUMN and not self.column_name:
            raise ValueError("При source_type='column' должен быть указан column_name")

        if self.source_type == FieldSourceTypeEnum.FIXED and self.fixed_value is None:
            raise ValueError("При source_type='fixed' должен быть указан fixed_value")

        if self.source_type == FieldSourceTypeEnum.CALLBACK and not self.callback:
            raise ValueError("При source_type='callback' должен быть указан callback")

        return self


class PeriodConfig(BaseModel):
    """Конфигурация периода"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Тип периода
    period_type: PeriodTypeEnum = Field(default=PeriodTypeEnum.YEARLY, description="Тип периода")

    # Поля периода
    period_year: FieldSourceDTO = Field(
        default_factory=lambda: FieldSourceDTO(), description="Источник данных для года периода"
    )

    period_month: Optional[FieldSourceDTO] = Field(default=None, description="Источник данных для месяца периода")
    period_quarter: Optional[FieldSourceDTO] = Field(default=None, description="Источник данных для квартала периода")
    period_week: Optional[FieldSourceDTO] = Field(default=None, description="Источник данных для недели периода")
    date_start: Optional[FieldSourceDTO] = Field(default=None, description="Источник данных для начала периода")
    date_end: Optional[FieldSourceDTO] = Field(default=None, description="Источник данных для конца периода")
    collected_at: Optional[FieldSourceDTO] = Field(default=None, description="Источник данных для даты сбора")
    meta_data: Optional[Dict[str, Any]] = Field(default=None, description="Дополнительные метаданные периода")

    @property
    def required_columns(self) -> List[str]:
        """Все обязательные колонки для периода"""

        columns = []

        # Проверяем каждое поле периода
        for field_name in [
            "period_year",
            "period_month",
            "period_quarter",
            "period_week",
            "date_start",
            "date_end",
            "collected_at",
        ]:
            field_source = getattr(self, field_name)
            if field_source and field_source.source_type == "column" and field_source.column_name:
                columns.append(field_source.column_name)

        return columns


class MetricConfig(BaseModel):
    """Конфигурация метрики"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # =========== Параметры заполнения таблицы metric_info
    # Основные данные
    slug: str = Field(max_length=255,description="Slug метрики (уникальный идентификатор)")
    name: str = Field(max_length=255, description="Название метрики")
    description: Optional[str] = Field(default=None, description="Описание метрики")
    category: CategoryMetricEnum = Field(description="Категория метрики")
    data_type: TypeDataEnum = Field(description="Тип данных")

    # Сведения об источнике
    source_name: Optional[str] = Field(default=None, max_length=255, description="Название источника")
    source_url: Optional[str] = Field(default=None, max_length=512, description="URL источника")

    # Параметры отображения
    show_in_country_list: bool = Field(default=False, description="Показывать в списке стран")
    show_in_country_detail: bool = Field(default=False, description="Показывать в детальной странице страны")
    show_in_city_list: bool = Field(default=False, description="Показывать в списке городов")
    show_in_city_detail: bool = Field(default=False, description="Показывать в детальной странице города")
    list_priority: int = Field(default=0, description="Приоритет в списках")
    detail_priority: int = Field(default=0, description="Приоритет в детальных страницах")
    is_primary: bool = Field(default=False, description="Основная метрика")
    is_secondary: bool = Field(default=False, description="Вспомогательная метрика")

    # Дополнительно
    meta_data: Optional[Dict[str, Any]] = Field(default=None, description="Дополнительные метаданные метрики")
    is_active: bool = Field(default=True, description="Активна ли метрика")

    # =========== Настройки для ETL
    # Основные настройки ETL
    value_column: str = Field(description="Столбец со значением метрики")
    value_transform: Optional[Callable[[Any], Any]] = Field(
        default=None, description="Функция для трансформации значения (очистка, приведение типа)"
    )
    country_column: str = Field(description="Столбец со страной")
    city_column: Optional[str] = Field(
        default=None, description="Столбец с городом (опционально)"
    )  # Опциональные поля для будущего расширения

    # =========== Параметры заполнения таблицы metric_series
    series_is_active: Optional[bool] = Field(default=True, description="Статус активности серии")
    series_is_preset: Optional[bool] = Field(default=False, description="Статус наличия пресета серии")
    series_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Дополнительные метаданные серии")

    # =========== Параметры заполнения таблицы metric_period
    period: PeriodConfig = Field(default_factory=lambda: PeriodConfig(), description="Конфигурация периода")

    # =========== Параметры атрибутов/фильтров
    attributes: List[AttributeConfig] = Field(default_factory=list, description="Конфигурация атрибутов/фильтров")


class CacheConfig(BaseModel):
    """Конфигурация для кэша"""

    country_size: int = Field(default=700)
    country_name: str = Field(default="country_cache")

    city_size: int = Field(default=5)
    city_name: str = Field(default="city_cache")

    metric_size: int = Field(default=5)
    metric_name: str = Field(default="metric_cache")

    series_size: int = Field(default=30000)
    series_name: str = Field(default="series_cache")

    period_size: int = Field(default=30000)
    period_name: str = Field(default="period_cache")

    attribute_type_size: int = Field(default=1000)
    attribute_type_name: str = Field(default="attribute_type_cache")

    attribute_value_size: int = Field(default=1000)
    attribute_value_name: str = Field(default="attribute_value_cache")


class ETLConfig(BaseModel):
    """Полная конфигурация ETL"""

    # Параллелизм
    max_workers: int = Field(default=8, description="Максимальное количество потоков")
    max_concurrent_chunks: int = Field(default=4, description="Максимальное количество параллельных чанков")
    chunk_size: int = Field(default=10000, description="Размер чанка для параллельной обработки")
    use_multiprocessing: bool = Field(default=False, description="Использовать multiprocessing для CPU-bound операций")

    # Оптимизации БД
    bulk_insert_method: str = Field(default="batch", description="Метод вставки: batch, vectorized, copy")
    batch_size: int = Field(default=5000, description="Размер батча для вставки")
    disable_indexes_during_import: bool = Field(default=False, description="Отключать индексы во время импорта")

    # Оптимизации памяти
    low_memory_mode: bool = Field(default=False, description="Режим низкого потребления памяти")
    cache_compression: bool = Field(default=True, description="Сжатие кэша в памяти")

    # =========== Параметры кэширования
    cache: CacheConfig = Field(default_factory=CacheConfig, title="Настройки кэша")
    max_workers: int = Field(default=8, title="Максимальное количестов воркеров")

    # =========== Параметры источника-файла с метриками
    name: str = Field(description="Название ETL, используется для логов")
    description: Optional[str] = Field(default=None, description="Описание ETL, используется для логов")
    csv_file: str = Field(description="Путь к CSV файлу")
    csv_delimiter: str = Field(",", description="Разделитель в CSV")
    csv_encoding: str = Field("utf-8", description="Кодировка CSV")

    # =========== Маппинг географических объектов метрики
    geography_level: GeographyLevelEnum = Field(description="Уровень географии")
    country_mapping: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Ключ: название в файле, Значение: список названий в БД (в колонке атрибута - country_column)",
    )

    country_column: str = Field(description="Колонка для сопоставления стран (name или name_eng)")
    city_mapping: Dict[str, List[str]] = Field(
        default_factory=dict, description="Маппинг названий городов"
    )  # Опциональные поля для будущего расширения

    # =========== Конфигурация метрик
    metric: MetricConfig = Field(description="Конфигурация метрики")

    # =========== Настройки загрузки данных в БД
    batch_size: int = Field(default=2000, description="Размер батча для вставки (увеличили для производительности)")
    skip_invalid_rows: bool = Field(default=True, description="Пропускать строки с ошибками")
    skip_duplicates: bool = Field(default=True, description="Пропускать дубликаты существующих записей")

    # =========== Дополнительные проверки
    validate_country_exists: bool = Field(default=True, description="Проверять существование страны в БД")

    @property
    def required_columns(self) -> Set[str]:
        """Все обязательные колонки из конфигурации"""

        required = set()

        # Колонки метрики
        required.add(self.metric.country_column)
        required.add(self.metric.value_column)

        if self.metric.city_column:
            required.add(self.metric.city_column)

        # Колонки периода
        for field_name in [
            "period_year",
            "period_month",
            "period_quarter",
            "period_week",
            "date_start",
            "date_end",
            "collected_at",
        ]:
            field_source = getattr(self.metric.period, field_name, None)
            if field_source and field_source.source_type == "column" and field_source.column_name:
                required.add(field_source.column_name)

        # Колонки атрибутов
        for attr in self.metric.attributes:
            required.add(attr.csv_column)

        return required

    @model_validator(mode="after")
    def validate_geography_level(self):
        """Валидация уровня географии"""

        if self.geography_level == GeographyLevelEnum.CITY and not self.metric.city_column:
            raise ValueError(f"Для geography_level='city' метрика '{self.metric.name}' должна иметь city_column")
        return self
