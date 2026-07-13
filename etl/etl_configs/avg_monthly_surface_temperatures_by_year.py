# etl/etl_configs/avg_monthly_surface_temperatures_by_year.py
"""
Конфигурация для загрузки данных
'Monthly average surface temperatures by year'
'Среднемесячные температуры поверхности по годам'
"""
from etl.config.etl_config import (
    AttributeConfig,
    AttributeParsingStrategyEnum,
    ComplexParseResultDTO,
    ETLConfig,
    FieldSourceDTO,
    FieldSourceTypeEnum,
    MetricConfig,
    PeriodConfig,
    PeriodDataDTO,
)
from src.core.enums import (
    CategoryMetricEnum,
    GeographyLevelEnum,
    PeriodTypeEnum,
    TypeDataEnum,
)


def parse_column_month(value: str) -> ComplexParseResultDTO:
    """Парсит колонку месяца и возвращает месяц"""

    period_data = PeriodDataDTO()
    period_data.period_month = int(value)

    return ComplexParseResultDTO(period_data=period_data)


def create_avg_monthly_surface_temperatures_by_year_etl_config() -> ETLConfig:
    """Создает конфигурацию для загрузки данных
    'Monthly average surface temperatures by year'
    'Среднемесячные температуры поверхности по годам'
    """

    # Конфигурация метрики
    metric_config = MetricConfig(
        # =========== Параметры заполнения таблицы metric_info
        # Основные данные
        slug="Monthly average surface temperatures by year",
        name="Среднемесячные температуры поверхности по годам",
        description="Среднемесячные температуры поверхности по годам",
        category=CategoryMetricEnum.UNCATEGORIZED,
        data_type=TypeDataEnum.FLOAT,
        # Сведения об источнике
        source_name="Our World In Data",
        source_url="https://ourworldindata.org/grapher/monthly-average-surface-temperatures-by-year?tab=table&time=latest&tableFilter=niaid",
        # Дополнительно
        meta_data=None,
        is_active=True,
        # =========== Настройки для ETL
        # Основные настройки ETL
        value_column="Value",
        country_column="Code",
        # Опциональные поля для будущего расширения
        city_column=None,
        # =========== Параметры заполнения таблицы metric_series
        # ...
        # =========== Параметры заполнения таблицы metric_period
        period=PeriodConfig(
            period_type=PeriodTypeEnum.MONTHLY,
            period_year=FieldSourceDTO(
                source_type=FieldSourceTypeEnum.COLUMN,
                column_name="Year",
                transform_callback=float,
            ),
        ),
        # =========== Параметры атрибутов/фильтров
        attributes=[
            AttributeConfig(
                # Основные данные
                csv_column="Month",
                # Стратегия парсинга
                parsing_strategy=AttributeParsingStrategyEnum.COMPLEX,
                complex_parser=parse_column_month,
            ),
            AttributeConfig(
                # Основные данные
                csv_column="Degrees",
                # Стратегия парсинга
                parsing_strategy=AttributeParsingStrategyEnum.FIXED_TYPE,
                attribute_type_code="Degrees",
                attribute_type_name="Градусы",
            ),
        ],
    )

    # Полная конфигурация ETL
    config = ETLConfig(
        # =========== Параметры источника-файла с метриками
        name="Monthly average surface temperatures by year",
        description="Импорт данных 'Monthly average surface temperatures by year' из CSV",
        csv_file="data/convert_files/convert_monthly-average-surface-temperatures-by-year.csv",
        csv_delimiter=";",
        csv_encoding="utf-8-sig",
        # =========== Маппинг географических объектов метрики
        geography_level=GeographyLevelEnum.COUNTRY,
        # country_mapping={},
        country_column="iso_alpha_3",
        # =========== Конфигурация метрик
        metric=metric_config,
        # =========== Настройки загрузки данных в БД
        batch_size=1000,
        skip_invalid_rows=True,
        skip_duplicates=True,
        # =========== Дополнительные проверки
        validate_country_exists=True,
    )

    return config
