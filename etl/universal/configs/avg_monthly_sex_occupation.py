"""
Конфигурация для загрузки данных 'Средний ежемесячный заработок сотрудников в зависимости от пола и профессии'
"""

from typing import List

from etl.universal.config_schema import (
    AttributeConfig,
    AttributeParsingStrategyEnum,
    AttributeTypeDTO,
    AttributeValueDTO,
    ComplexParseResultDTO,
    ETLConfig,
    FieldSourceDTO,
    FieldSourceTypeEnum,
    MetricConfig,
    ParsedAttributeDTO,
    PeriodConfig,
    PeriodDataDTO,
)
from src.core.enums import (
    CategoryMetricEnum,
    GeographyLevelEnum,
    PeriodTypeEnum,
    TypeDataEnum,
)


def parse_column_full_data_complex(value: str) -> ComplexParseResultDTO:
    """Парсит сложную строку из FULL_DATA:
    "Job coverage: Main job currently held | Working time arrangement coverage: Full-time and part time workers |
    Working time concept: Hours actually worked | Currency: ABW - Florin (AWG) | Data reference period: September"

    Возвращает:
    - список атрибутов с их настройками
    - данные периода (если есть)
    """

    attributes: List[ParsedAttributeDTO] = []
    period_data: PeriodDataDTO = PeriodDataDTO()

    if not value:
        return ComplexParseResultDTO()

    # Разделяем на части по '|'
    parts = [part.strip() for part in value.split(" | ")]

    ATTRIBUTES_NOT_FILTERED = (
        "Accounting concept:",
        "Age coverage:",
        "Central tendency measure:",
        "Components of earnings/wages:",
        "Economic activity coverage:",
        "Employment definition:",
        "Establishment size coverage:",
        "Geographical coverage:",
        "Institutional sector coverage:",
        "Job coverage:",
        "Population coverage:",
        "Reference group coverage:",
        "Remarks:",
        "Repository:",
        "Unemployment definition:",
        "Value type:",
        "Working time arrangement coverage:",
        "Working time concept:",
    )

    for part in parts:
        if any(key in part for key in ATTRIBUTES_NOT_FILTERED):
            type_code, value_code = part.split(": ", 1)  # Разделяем только по первому вхождению ": "
            attributes.append(
                ParsedAttributeDTO(
                    type=AttributeTypeDTO(code=type_code, name=type_code),
                    value=AttributeValueDTO(
                        code=value_code[:255],
                        name=value_code[:255],
                        meta_data={"code": value_code} if len(value_code) > 255 else None,
                    ),
                )
            )
        elif "Break in series: Methodology revised:" in part:
            attributes.append(
                ParsedAttributeDTO(
                    type=AttributeTypeDTO(code="OBS status", name="Статус наблюдения"),
                    value=AttributeValueDTO(code=part, name=part),
                )
            )
        elif "Currency:" in part:
            type_code, value_code = part.split(": ", 1)  # Разделяем только по первому вхождению ": "
            attributes.append(
                ParsedAttributeDTO(
                    type=AttributeTypeDTO(code=type_code, name=type_code, is_filtered=True),
                    value=AttributeValueDTO(code=value_code, name=value_code, is_filtered=True),
                )
            )

        elif "Data reference period:" in part:
            mapped_month_data = {"April": 4, "May": 5, "June": 6, "July": 7, "August": 8, "September": 9, "October": 10}
            mapped_year_data = {"Noncalendar year": 1, "End of the year": 12}
            mapped_semester_data = {"First semester": 6, "Second semester": 12}
            mapped_quarter_data = {"Second quarter": 2, "Third quarter": 3, "Fourth quarter": 4}
            value = part[23:]
            if value in mapped_month_data.keys():
                period_data.period_month = mapped_month_data.get(value)
            elif value in mapped_semester_data.keys():
                period_data.period_month = mapped_semester_data.get(value)
            elif value in mapped_year_data.keys():
                period_data.period_month = mapped_year_data.get(value)
            elif value in mapped_quarter_data.keys():
                period_data.period_month = mapped_quarter_data.get(value)

    return ComplexParseResultDTO(attributes=attributes, period_data=period_data)


def parse_sex_label(value: str) -> ParsedAttributeDTO:
    """Кастомный парсер для колонки sex.label
    Примеры значений: "Total", "Male", "Female", "Other"
    """

    mapped_dict = {"Total": "Общий", "Male": "Мужской", "Female": "Женский", "Other": "Другое"}
    result: ParsedAttributeDTO = ParsedAttributeDTO(
        type=AttributeTypeDTO(code="Sex", name="Пол", is_filtered=True),
        value=AttributeValueDTO(code=value, name=mapped_dict[value], is_filtered=True),
    )
    return result


def parse_classif_1_label(value: str) -> ParsedAttributeDTO:
    """Кастомный парсер для колонки classif1.label
    Примеры значений:
    - "Occupation (Skill level): Skill level 1 ~ low"
    - "Occupation (ISCO-08): 7. Craft and related trades workers"
    - "Occupation (ISCO-08): Total"
    """

    type, value = value.split(": ", 1)
    result: ParsedAttributeDTO = ParsedAttributeDTO(
        type=AttributeTypeDTO(code=type, name=type),
        value=AttributeValueDTO(code=value, name=value),
    )
    return result


def parse_classif_2_label(value: str) -> ParsedAttributeDTO:
    """Кастомный парсер для колонки classif2.label
    Примеры значений:
    - "Currency: Local currency"
    - "Currency: 2021 PPP $"
    - "Currency: U.S. dollars"
    """

    result: ParsedAttributeDTO = ParsedAttributeDTO(
        type=AttributeTypeDTO(code="Currency", name="Валюта"),
        value=AttributeValueDTO(code=value[10:], name=value[10:], is_filtered=True),
    )
    return result


def parse_obs_status_label(value: str) -> ParsedAttributeDTO:
    """Кастомный парсер для колонки obs_status.label
    Примеры значений:
    - "Break in series"
    - "Unreliable"
    """

    result: ParsedAttributeDTO = ParsedAttributeDTO(
        type=AttributeTypeDTO(code="OBS status", name="Статус наблюдения"),
        value=AttributeValueDTO(code=value, name=value),
    )
    return result


def parse_note_classif_label(value: str) -> ParsedAttributeDTO:
    """Кастомный парсер для колонки note_classif.label
    Примеры значений:
    - "Occupation (ISCO-88): Nonstandard occupation - Including 6"
    - "Occupation (ISCO-88): Nonstandard occupation - Including 3"
    """

    type_code, value_name = value.split(": ")
    result: ParsedAttributeDTO = ParsedAttributeDTO(
        type=AttributeTypeDTO(code=type_code, name=type_code),
        value=AttributeValueDTO(code=value_name, name=value_name),
    )
    return result


def create_avg_monthly_earnings_employees_sex_occupation_etl_config() -> ETLConfig:
    """Создает конфигурацию для загрузки данных
    'Средний ежемесячный заработок сотрудников в зависимости от пола и профессии'"""

    # Конфигурация метрики
    metric_config = MetricConfig(
        # =========== Параметры заполнения таблицы metric_info
        # Основные данные
        slug="Average monthly earnings of employees by sex and occupation",
        name="Средний ежемесячный заработок сотрудников в зависимости от пола и профессии",
        description="Средний ежемесячный заработок сотрудников в зависимости от пола и профессии",
        category=CategoryMetricEnum.ECONOMY,
        data_type=TypeDataEnum.FLOAT,
        # Сведения об источнике
        source_name="ILOSTAT",
        source_url="https://rshiny.ilo.org/dataexplorer06/?lang=en&segment=indicator&id=EAR_4MTH_SEX_OCU_CUR_NB_A",
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
        value_column="obs_value",
        country_column="ref_area.label",
        # Опциональные поля для будущего расширения
        city_column=None,
        # =========== Параметры заполнения таблицы metric_series
        # series_is_active=True,
        # series_is_preset=False,
        # series_metadata=None,
        # =========== Параметры заполнения таблицы metric_period
        period=PeriodConfig(
            period_type=PeriodTypeEnum.YEARLY,
            period_year=FieldSourceDTO(
                source_type=FieldSourceTypeEnum.COLUMN,
                column_name="time",
                transform_callback=lambda x: int(x) if x else None,
            ),
        ),
        # =========== Параметры атрибутов/фильтров
        attributes=[
            AttributeConfig(
                # Основные данные
                csv_column="source.label",
                # Стратегия парсинга
                parsing_strategy=AttributeParsingStrategyEnum.FIXED_TYPE,
                attribute_type_code="Source",
                attribute_type_name="Источник",
            ),
            AttributeConfig(
                # Основные данные
                csv_column="sex.label",
                # Стратегия парсинга
                parsing_strategy=AttributeParsingStrategyEnum.CUSTOM,
                custom_parser=parse_sex_label,
            ),
            AttributeConfig(
                # Основные данные
                csv_column="classif1.label",
                # Стратегия парсинга
                parsing_strategy=AttributeParsingStrategyEnum.CUSTOM,
                custom_parser=parse_classif_1_label,
            ),
            AttributeConfig(
                # Основные данные
                csv_column="classif2.label",
                # Стратегия парсинга
                parsing_strategy=AttributeParsingStrategyEnum.CUSTOM,
                custom_parser=parse_classif_2_label,
            ),
            AttributeConfig(
                # Основные данные
                csv_column="obs_status.label",
                # Стратегия парсинга
                parsing_strategy=AttributeParsingStrategyEnum.CUSTOM,
                custom_parser=parse_obs_status_label,
            ),
            AttributeConfig(
                # Основные данные
                csv_column="note_classif.label",
                # Стратегия парсинга
                parsing_strategy=AttributeParsingStrategyEnum.CUSTOM,
                custom_parser=parse_note_classif_label,
            ),
            AttributeConfig(
                # Основные данные
                csv_column="FULL_DATA",
                # Стратегия парсинга
                parsing_strategy=AttributeParsingStrategyEnum.COMPLEX,
                complex_parser=parse_column_full_data_complex,
            ),
        ],
    )

    # Полная конфигурация ETL
    config = ETLConfig(
        # =========== Параметры источника-файла с метриками
        name="Average monthly earnings of employees by sex and occupation",
        description="Импорт данных 'Average monthly earnings of employees by sex and occupation' из CSV",
        csv_file="data/EAR_4MTH_SEX_OCU_CUR_NB_A&timefrom=2000&timeto=2025&type=label&format.csv",
        csv_delimiter=";",
        csv_encoding="utf-8-sig",
        # =========== Маппинг географических объектов метрики
        geography_level=GeographyLevelEnum.COUNTRY,
        country_mapping={
            "Bolivia (Plurinational State of)": ["Bolivia"],
            "Brunei Darussalam": ["Brunei"],
            "Côte d'Ivoire": ["Ivory Coast"],
            "Hong Kong, China": ["Hong Kong"],
            "Lao People's Democratic Republic": ["Laos"],
            "Macao, China": ["Macao"],
            "Occupied Palestinian Territory": ["Palestine"],
            "Republic of Korea": ["South Korea"],
            "Republic of Moldova": ["Moldova"],
            "Russian Federation": ["Russia"],
            "Tanzania, United Republic of": ["Tanzania"],
            "United Kingdom of Great Britain and Northern Ireland": ["Great Britain", "Ireland"],
            "United States of America": ["USA"],
            "Venezuela (Bolivarian Republic of)": ["Venezuela"],
            "Viet Nam": ["Vietnam"],
            "Marshall Islands": ["Marshall Islands"],
            "Australia": ["Australia"],
            "Bermuda": ["Bermuda"],
            "Botswana": ["Botswana"],
            "Bosnia and Herzegovina": ["Bosnia and Herzegovina"],
            "Curaçao": ["Curaçao"],
            "Congo": ["Congo Republic"],
            "Congo, Democratic Republic of the": ["DR Congo"],
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
