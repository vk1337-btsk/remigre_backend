# etl/services/data_parser.py
"""
Преобразование строки DataFrame в структурированный словарь (RawRecord).
Никакой работы с БД или кэшем.
"""

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from typing_extensions import TypedDict

from etl.config.config_schema import (
    AttributeParsingStrategyEnum,
    AttributeTypeDTO,
    AttributeValueDTO,
    ETLConfig,
    FieldSourceDTO,
    FieldSourceTypeEnum,
    ParsedAttributeDTO,
    PeriodConfig,
    PeriodDataDTO,
)
from src.core.config.logging import setup_logger_to_file
from src.core.enums import GeographyLevelEnum


logger = setup_logger_to_file()


class RawRecord(TypedDict):
    """Сырая запись после парсинга строки CSV."""

    country_name: str
    city_name: Optional[str]
    raw_value: Any
    attributes: List[ParsedAttributeDTO]
    period_data: PeriodDataDTO
    series_hash: Optional[str]  # будет заполнен после получения ID атрибутов


class DataParser:
    """Только парсинг строк, без side-эффектов."""

    def __init__(self, config: ETLConfig):
        """Инициализация параметров"""

        self.config = config
        self.metric_config = config.metric

    def parse_chunk(self, chunk_df: pd.DataFrame) -> List[RawRecord]:
        """Преобразовывает DataFrame из pandaas в список RawRecord (синхронно)."""

        records = []
        chunk_dict = chunk_df.to_dict("records")

        # Прохожусь по записям и обрабатываю строки
        for row in chunk_dict:
            record = self._parse_row(row)  # pyright: ignore[reportArgumentType]
            if record:
                records.append(record)

        return records

    def _parse_row(self, row: Dict[str, str]) -> Optional[RawRecord]:
        """Общий метод парсингп одной строки файла.
        Принимаем строку и на выходе получаем RawRecord готовую строку с обработанными данными.
        """

        # Проверяем наличие значения и применяем трансформацию значения (если указана)
        value = row.get(self.metric_config.value_column, "").strip()
        if not value:
            return None

        value = self.metric_config.value_transform(value) if self.metric_config.value_transform else value

        # Проверяем наличие страны
        country = row.get(self.metric_config.country_column, "").strip()
        if not country:
            return None

        # Проверяем наличие города (если есть)
        city = None
        if self.config.geography_level == GeographyLevelEnum.CITY and self.metric_config.city_column:
            city = row.get(self.metric_config.city_column, "").strip()
            if not city:
                city = None

        # Парсим атрибуты и период из строки
        attributes, complex_periods = self._parse_attributes(row)

        # Формируем PeriodDataDTO из конфига + комплексных периодов
        period_data = self._collect_period_data(
            row=row, config_period=self.metric_config.period, complex_periods=complex_periods
        )

        # Формируем готовый объект RawRecord с данными из строки
        result = RawRecord(
            country_name=country,
            city_name=city,
            raw_value=value,
            attributes=attributes,
            period_data=period_data,
            series_hash=None,  # Заполним позже в EntityResolver
        )
        return result

    def _parse_attributes(self, row: Dict[str, str]) -> Tuple[List[ParsedAttributeDTO], List[PeriodDataDTO]]:
        """Принимает строку. Парсит и преобразует все атрибуты из строки описанные в конфиге.
        Возвращает кортеж из списка обработанных атрибутов и"""

        # Задаём результаты для возврата
        result_all_attrs = []
        complex_periods: List[PeriodDataDTO] = []

        # Проходимся по всем атрибутам
        for attr_cfg in self.metric_config.attributes:

            # Получаем значение и проверяем на наличие
            val = row.get(attr_cfg.csv_column, "").strip()

            # Если значения нет - пропускаем
            if pd.isna(val) or val == "":
                continue

            # Преобразуем атрибуты и период исходя из стратегии парсинга
            # Если стратегия - фиксированная
            if attr_cfg.parsing_strategy == AttributeParsingStrategyEnum.FIXED_TYPE:
                # В этом случае у нас для type заполняются только code и name из атрибутов, а
                # а остальное берётся из значений по умолчанию, если не переопределено
                # Для value - code и name берётся из значения, а остальное по умолчанию, если не переопределено
                attr = ParsedAttributeDTO(
                    type=AttributeTypeDTO(
                        code=attr_cfg.attribute_type_code if attr_cfg.attribute_type_code else "",
                        name=attr_cfg.attribute_type_name if attr_cfg.attribute_type_name else "",
                        value_type=attr_cfg.default_type_value_type,
                        is_active=attr_cfg.default_type_is_active,
                        is_filtered=attr_cfg.default_type_is_filtered,
                        sort_order=attr_cfg.default_type_sort_order,
                        meta_data=attr_cfg.default_type_meta_data,
                    ),
                    value=AttributeValueDTO(
                        code=str(val),
                        name=str(val),
                        is_active=attr_cfg.default_value_is_active,
                        is_filtered=attr_cfg.default_value_is_filtered,
                        sort_order=attr_cfg.default_value_sort_order,
                        meta_data=attr_cfg.default_value_meta_data,
                    ),
                )
                result_all_attrs.append(attr)

            # Если стратегия - кастомный парсер
            elif attr_cfg.parsing_strategy == AttributeParsingStrategyEnum.CUSTOM:
                if attr_cfg.custom_parser:
                    try:
                        result = attr_cfg.custom_parser(str(val))
                        if result:
                            result_all_attrs.append(result)
                    except Exception as e:
                        logger.error(
                            f"Стратегия парсинга CUSTOM. Ошибка в custom_parser для {attr_cfg.csv_column}: {e}"
                        )
                else:
                    logger.error(f"Стратегия парсинга CUSTOM. Ошибка custom_parser для {attr_cfg.csv_column} не задан")

            # Если стратегия - комплексный подход
            elif attr_cfg.parsing_strategy == AttributeParsingStrategyEnum.COMPLEX:
                if attr_cfg.complex_parser:
                    try:
                        result = attr_cfg.complex_parser(str(val))
                        result_all_attrs.extend(result.attributes)

                        if result.period_data:
                            complex_periods.append(result.period_data)

                    except Exception as e:
                        logger.debug(
                            f"Стратегия парсинга COMPLEX. Ошибка в complex_parser для {attr_cfg.csv_column}: {e}"
                        )
                else:
                    logger.error(
                        f"Стратегия парсинга COMPLEX. Ошибка complex_parser для {attr_cfg.csv_column} не задан"
                    )

        return result_all_attrs, complex_periods

    def _collect_period_data(
        self, row: Dict[str, str], config_period: Optional[PeriodConfig], complex_periods: List[PeriodDataDTO]
    ) -> PeriodDataDTO:
        """Сборка единого PeriodDataDTO:
        - За основу берётся период, сформированный из конфига.
        - Комплексные периоды ТОЛЬКО ДОПОЛНЯЮТ незаполненные поля.
        - При конфликте (конфиг ≠ комплекс) приоритет у конфига, конфликт логируется.
        - Всегда возвращается объект PeriodDataDTO (даже полностью пустой).
        """

        # Формируем PeriodDataDTO из конфига (может вернуться пустой PeriodDataDTO, если нет данных)
        period_dto = self._build_period_from_config(row, config_period)

        # Если нет комплексных периодов — возвращаем то, что есть, либо пустой период
        if not complex_periods:
            return period_dto if period_dto is not None else PeriodDataDTO()

        # Дополняем период из всех комплексных периодов
        for idx, complex_period in enumerate(complex_periods, start=1):
            # Поля года, месяца, квартала, недели, дат и collected_at
            for field in [
                "period_year",
                "period_month",
                "period_quarter",
                "period_week",
                "date_start",
                "date_end",
                "collected_at",
            ]:
                # Получаем значение из комплексного периода
                val = getattr(complex_period, field)
                if val is None:
                    continue

                # Получаем значение из текущего period_dto
                current = getattr(period_dto, field)
                if current is None:
                    setattr(period_dto, field, val)

                # Логгируем конфликт
                elif current != val:
                    logger.warning(
                        f"Конфликт периода: поле {field} уже задано ({current}), "
                        f"комплексный период #{idx} даёт {val} — оставлено значение из конфига"
                    )

            # Определяем period_type для PeriodDataDTO
            if complex_period.period_type is not None and period_dto.period_type is None:
                period_dto.period_type = complex_period.period_type
            elif complex_period.period_type is not None and period_dto.period_type != complex_period.period_type:
                logger.warning(
                    f"Конфликт периода: period_type уже {period_dto.period_type}, "
                    f"комплексный период #{idx} даёт {complex_period.period_type} — оставлено значение из конфига"
                )
            # Определяем meta_data для PeriodDataDTO
            if complex_period.meta_data is not None and period_dto.meta_data is None:
                period_dto.meta_data = complex_period.meta_data
            elif complex_period.meta_data is not None and period_dto.meta_data != complex_period.meta_data:
                logger.warning(
                    f"Конфликт периода: meta_data уже задана, "
                    f"комплексный период #{idx} даёт другие данные — оставлено значение из конфига"
                )

        return period_dto

    def _build_period_from_config(self, row: Dict[str, str], config_period: Optional[PeriodConfig]) -> PeriodDataDTO:
        """Создаёт PeriodDataDTO на основе конфига. Возвращает None, если ни одно поле не удалось заполнить."""

        if config_period is None:
            logger.debug(f"PeriodConfig не был задан. Создаём пустой")
            return PeriodDataDTO()

        period = PeriodDataDTO(period_type=config_period.period_type, meta_data=config_period.meta_data)

        fields_map = {
            "period_year": config_period.period_year,
            "period_month": config_period.period_month,
            "period_quarter": config_period.period_quarter,
            "period_week": config_period.period_week,
            "date_start": config_period.date_start,
            "date_end": config_period.date_end,
            "collected_at": config_period.collected_at,
            "meta_data": config_period.meta_data,
        }

        # Проходимя по ячейкам
        for field_name, source in fields_map.items():
            value = self._resolve_field_source(row, source)
            if value is not None:
                setattr(period, field_name, value)

        return period

    def _resolve_field_source(self, row: Dict[str, str], source: Optional[FieldSourceDTO]) -> Optional[Any]:
        """Получаем значение согласно инструкции источника"""

        if not source:
            return None

        value = None

        # Получаем значение, исходя из тактики получения данных
        if source.source_type == FieldSourceTypeEnum.COLUMN:
            raw = row.get(source.column_name or "", "").strip()
            if raw:
                value = raw

        elif source.source_type == FieldSourceTypeEnum.FIXED:
            value = source.fixed_value

        elif source.source_type == FieldSourceTypeEnum.CALLBACK:
            if source.callback:
                value = source.callback(row)
            else:
                logger.error(f"Для source_type.CALLBACK не указан source.callback {source=} для {row=}")

        else:
            raise ValueError(f"Неизвестный source_type у ячейки {source=} для {row=}")

        # Трансформируем значение
        if value is not None and source.transform_callback:
            value = source.transform_callback(value)

        return value
