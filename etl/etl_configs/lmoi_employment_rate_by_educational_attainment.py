# etl/etl_configs/lmoi_employment_rate_by_educational_attainment.py
"""
Конфигурация для загрузки данных
'Labour market outcomes of immigrants - Employment rates by educational attainment'
'Результаты трудоустройства иммигрантов: уровень занятости в зависимости от уровня образования'
"""
from decimal import ROUND_HALF_UP, Decimal
from typing import List, Optional, Union

from etl.config.config_schema import (
    AttributeConfig,
    AttributeParsingStrategyEnum,
    AttributeTypeDTO,
    AttributeValueDTO,
    ETLConfig,
    FieldSourceDTO,
    FieldSourceTypeEnum,
    MetricConfig,
    ParsedAttributeDTO,
    PeriodConfig,
)
from src.core.enums import (
    CategoryMetricEnum,
    GeographyLevelEnum,
    PeriodTypeEnum,
    TypeDataEnum,
)


def parse_column_sex(value: str) -> ParsedAttributeDTO:
    """Кастомный парсер для колонки Sex
    Примеры значений: "Total", "Male", "Female",
    """

    mapped_dict = {"Total": "Общий", "Male": "Мужской", "Female": "Женский"}
    result: ParsedAttributeDTO = ParsedAttributeDTO(
        type=AttributeTypeDTO(code="Sex", name="Пол", is_filtered=True),
        value=AttributeValueDTO(code=value, name=mapped_dict[value], is_filtered=True),
    )
    return result


def value_transform(value: Optional[Union[str, float, int]]) -> Optional[Decimal]:
    """Преобразует значение в Decimal с двумя знаками после запятой."""

    try:
        if value is None:
            return None
        elif isinstance(value, str):
            cleaned = value.replace(",", ".")
            new_value = Decimal(cleaned)
        elif isinstance(value, (float, int)):
            new_value = Decimal(str(value))
        else:
            raise ValueError(f"Неизвестный тип данных {type(value)=} для значения {value=}")
        return new_value
    except Exception as error:
        raise ValueError(f"Ошибка при преобразовании значения {value=}. Ошибка: {error=}")


def create_lmoi_employment_rate_by_educational_attainment_etl_config() -> ETLConfig:
    """Создает конфигурацию для загрузки данных
        'Labour market outcomes of immigrants - Employment rates by educational attainment'
    'Результаты трудоустройства иммигрантов: уровень занятости в зависимости от уровня образования'"""

    # Конфигурация метрики
    metric_config = MetricConfig(
        # =========== Параметры заполнения таблицы metric_info
        # Основные данные
        slug="Labour market outcomes of immigrants - Employment rates by educational attainment",
        name="Результаты трудоустройства иммигрантов: занятость, безработица и участие в рабочей силе в зависимости от пола",
        description="Результаты трудоустройства иммигрантов: уровень занятости в зависимости от уровня образования",
        category=CategoryMetricEnum.EMIGRATION,
        data_type=TypeDataEnum.FLOAT,
        # Сведения об источнике
        source_name="OECD Data Explorer",
        source_url="https://data-explorer.oecd.org/vis?df[ds]=DisseminateFinalDMZ&df[id]=DSD_MIG%40DF_MIG_EMP_EDU&df[ag]=OECD.ELS.IMD&dq=..A.....&pd=2000%2C2024&to[TIME_PERIOD]=false",
        # Параметры отображения
        show_in_country_list=True,
        show_in_country_detail=True,
        show_in_city_list=False,
        show_in_city_detail=False,
        list_priority=0,
        detail_priority=0,
        is_primary=True,
        is_secondary=True,
        # Дополнительно
        meta_data=None,
        is_active=True,
        # =========== Настройки для ETL
        # Основные настройки ETL
        value_column="OBS_VALUE",
        value_transform=value_transform,
        country_column="Reference area",
        # Опциональные поля для будущего расширения
        city_column=None,
        # =========== Параметры заполнения таблицы metric_series
        # ...
        # =========== Параметры заполнения таблицы metric_period
        period=PeriodConfig(
            period_type=PeriodTypeEnum.YEARLY,
            period_year=FieldSourceDTO(
                source_type=FieldSourceTypeEnum.COLUMN,
                column_name="TIME_PERIOD",
                transform_callback=int,
            ),
        ),
        # =========== Параметры атрибутов/фильтров
        attributes=[
            AttributeConfig(
                # Основные данные
                csv_column="Measure",
                # Стратегия парсинга
                parsing_strategy=AttributeParsingStrategyEnum.FIXED_TYPE,
                attribute_type_code="Central tendency measure",
                attribute_type_name="Central tendency measure",
            ),
            AttributeConfig(
                # Основные данные
                csv_column="Sex",
                # Стратегия парсинга
                parsing_strategy=AttributeParsingStrategyEnum.FIXED_TYPE,
                attribute_type_code="Sex",
                attribute_type_name="Sex",
            ),
            AttributeConfig(
                # Основные данные
                csv_column="Education level",
                # Стратегия парсинга
                parsing_strategy=AttributeParsingStrategyEnum.FIXED_TYPE,
                attribute_type_code="Education level",
                attribute_type_name="Education level",
            ),
            AttributeConfig(
                # Основные данные
                csv_column="Place of birth",
                # Стратегия парсинга
                parsing_strategy=AttributeParsingStrategyEnum.FIXED_TYPE,
                attribute_type_code="Place of birth",
                attribute_type_name="Place of birth",
            ),
            AttributeConfig(
                # Основные данные
                csv_column="Unit of measure",
                # Стратегия парсинга
                parsing_strategy=AttributeParsingStrategyEnum.FIXED_TYPE,
                attribute_type_code="Central tendency measure",
                attribute_type_name="Central tendency measure",
            ),
        ],
    )

    # Полная конфигурация ETL
    config = ETLConfig(
        # =========== Параметры источника-файла с метриками
        name="Labour market outcomes of immigrants - Employment, unemployment, and participation rates by sex",
        description="Импорт данных 'Labour market outcomes of immigrants - Employment, unemployment, and participation rates by sex' из CSV",
        csv_file="data/OECD.ELS.IMD,DSD_MIG@DF_MIG_EMP_EDU,+..A.csv",
        csv_delimiter=";",
        csv_encoding="utf-8-sig",
        # =========== Маппинг географических объектов метрики
        geography_level=GeographyLevelEnum.COUNTRY,
        country_mapping={
            "Korea": ["South Korea"],
            "Slovak Republic": ["Slovakia"],
            "United Kingdom": ["Great Britain"],
            "United States": ["USA"],
            "European Union (27 countries from 01/02/2020)": [
                "Austria",
                "Belgium",
                "Bulgaria",
                "Croatia",
                "Cyprus",
                "Czechia",
                "Denmark",
                "Estonia",
                "Finland",
                "France",
                "Germany",
                "Greece",
                "Hungary",
                "Ireland",
                "Italy",
                "Latvia",
                "Lithuania",
                "Luxembourg",
                "Malta",
                "Netherlands",
                "Poland",
                "Portugal",
                "Romania",
                "Slovakia",
                "Slovenia",
                "Spain",
                "Sweden",
            ],
            "European Union (27 countries)": [
                "Austria",
                "Belgium",
                "Bulgaria",
                "Croatia",
                "Cyprus",
                "Czechia",
                "Denmark",
                "Estonia",
                "Finland",
                "France",
                "Germany",
                "Greece",
                "Hungary",
                "Ireland",
                "Italy",
                "Latvia",
                "Lithuania",
                "Luxembourg",
                "Malta",
                "Netherlands",
                "Poland",
                "Portugal",
                "Romania",
                "Slovakia",
                "Slovenia",
                "Spain",
                "Sweden",
            ],
            "European Union (28 countries)": [
                "Austria",
                "Belgium",
                "Bulgaria",
                "Croatia",
                "Cyprus",
                "Czechia",
                "Denmark",
                "Estonia",
                "Finland",
                "France",
                "Germany",
                "Great Britain",
                "Greece",
                "Hungary",
                "Ireland",
                "Italy",
                "Latvia",
                "Lithuania",
                "Luxembourg",
                "Malta",
                "Netherlands",
                "Poland",
                "Portugal",
                "Romania",
                "Slovakia",
                "Slovenia",
                "Spain",
                "Sweden",
            ],
        },
        country_column="name_eng",
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
