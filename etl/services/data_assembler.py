# etl/services/data_assembler.py
"""
Сборка моделей MetricDataModel из сырых записей и маппингов.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional, Tuple, Union

from etl.config.config_schema import ETLConfig, PeriodDataDTO
from etl.services.data_parser import RawRecord
from src.core.config.logging import setup_logger_to_file
from src.core.enums import TypeDataEnum
from src.ms_metric.metrics import MetricDataModel


logger = setup_logger_to_file()


class DataAssembler:

    def __init__(self, config: ETLConfig):

        self.config = config
        self.metric_config = config.metric

    def assemble(
        self,
        raw_records: List[RawRecord],
        country_map: Dict[str, List[int]],
        series_map: Dict[str, int],
        period_map: Dict[str, int],
    ) -> List[MetricDataModel]:
        """Создаёт список моделей для вставки."""

        result = []
        for rec in raw_records:

            # Получаем ID стран
            country_ids = country_map.get(rec["country_name"])
            if not country_ids:  # пустой список или None
                continue

            # Формируем хэш серий
            series_hash = rec.get("series_hash")
            if not series_hash or series_hash not in series_map:
                continue
            series_id = series_map[series_hash]

            # Формируем ключ к периоду
            period_key = self._make_period_key(rec["period_data"])
            period_id = period_map.get(period_key)
            if not period_id:
                continue

            # Преобразование значения
            val_numeric, val_string, val_boolean, val_range_start, val_range_end = self._convert_value(rec["raw_value"])

            # Проверяем, что есть хотя бы одно значение (иначе нарушим CHECK в БД)
            if (
                val_numeric is None
                and val_string is None
                and val_boolean is None
                and val_range_start is None
                and val_range_end is None
            ):
                logger.warning(
                    f"Пропуск записи: все значения null для {rec.get('country_name')}, series_hash={series_hash}"
                )
                continue

            # Для каждой страны создаём отдельную запись
            for country_id in country_ids:
                model = MetricDataModel(
                    series_id=series_id,
                    period_id=period_id,
                    country_id=country_id,
                    city_id=rec.get(
                        "city_name"
                    ),  # если есть, но ID ещё не получен – в этой версии города не поддерживаем
                    value_numeric=val_numeric,
                    value_string=val_string,
                    value_boolean=val_boolean,
                    value_range_start=val_range_start,
                    value_range_end=val_range_end,
                )
                result.append(model)

        return result

    def _convert_value(
        self, raw: Any
    ) -> Tuple[Optional[Union[float, Decimal]], Optional[str], Optional[bool], Optional[float], Optional[float]]:
        """Преобразует строковое значение в соответствии с типом метрики."""

        if not raw:
            return None, None, None, None, None

        value_numeric = None
        value_string = None
        value_boolean = None
        value_range_start = None
        value_range_end = None

        try:
            # Если тип значения FLOAT
            if self.metric_config.data_type == TypeDataEnum.FLOAT:

                if isinstance(raw, str):
                    cleaned = raw.replace(",", ".")  # Заменяем запятую на точку
                    value_numeric = Decimal(cleaned) if cleaned else None

                elif isinstance(raw, int) or isinstance(raw, float) or isinstance(raw, Decimal):
                    value_numeric = Decimal(str(raw))

                else:
                    logger.warning(f"Тип значение FLOAT, но получен {raw=}, {type(raw)=}")

            # Если тип значения STRING
            elif self.metric_config.data_type == TypeDataEnum.STRING:
                value_string = str(raw)

            # Если тип значения BOOL
            elif self.metric_config.data_type == TypeDataEnum.BOOL:
                if isinstance(raw, str):
                    value_boolean = raw.lower() in ["true", "yes", "1", "да"]
                else:
                    value_boolean = bool(raw)

            # Если тип значения RANGE
            elif self.metric_config.data_type == TypeDataEnum.RANGE:
                if "-" in raw:
                    parts = raw.split("-")
                    if len(parts) == 2:
                        value_range_start = float(parts[0].replace(",", ".")) if parts[0] else None
                        value_range_end = float(parts[1].replace(",", ".")) if parts[1] else None

            else:
                logger.error(f"Неизвестный тип данных: {self.metric_config.data_type}")

        except (ValueError, AttributeError) as e:
            logger.warning(f"Не удалось преобразовать значение '{raw}' (тип {self.metric_config.data_type}): {e}")
            return None, None, None, None, None

        return value_numeric, value_string, value_boolean, value_range_start, value_range_end

    @staticmethod
    def _make_period_key(p: PeriodDataDTO) -> str:
        """Генерирует ключ периода, идентичный тому, что используется в EntityResolver."""
        key = f"{p.period_type}_{p.period_year}"
        if p.period_month:
            key += f"_{p.period_month}"
        if p.period_quarter:
            key += f"_q{p.period_quarter}"
        if p.period_week:
            key += f"_w{p.period_week}"
        return key
