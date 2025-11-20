"""
Скрипт для заполнения БД данными о средней месячной ЗП по полу и роду деятельности
Скачал данные отсюда: https://rshiny.ilo.org/dataexplorer06/?lang=en&segment=indicator&id=EAR_4MTH_SEX_OCU_CUR_NB_A#
Файл в data: EAR_4MTH_SEX_OCU_CUR_NB_A-filtered-2025-11-01
"""

import asyncio
import csv
from pathlib import Path
from typing import Dict, List, Sequence, Union, cast

from src.core.config.logging import setup_logger_to_file
from src.core.database.db_config import AsyncSessionLocal
from src.ms_location.dto import CountryGetDTO
from src.ms_location.models import CountryModel
from src.ms_metric.dto import (
    MetricInfoCreateDTO,
    MetricPeriodCreateDTO,
    MetricSeriesCreateDTO,
)
from src.ms_metric.enums import CategoryMetricEnum, PeriodTypeEnum, TypeDataEnum
from src.ms_metric.models import (
    MetricDataModel,
    MetricInfoModel,
    MetricPeriodModel,
    MetricSeriesModel,
)


logger = setup_logger_to_file()

# === Требуемые колонки ===
REQUIRED_COLUMNS = {
    "ref_area.label",
    "source.label",
    "indicator.label",
    "sex.label",
    "classif1.label",
    "classif2.label",
    "time",
    "obs_value",
    "obs_status.label",
    "note_classif.label",
    "note_indicator.label",
    "note_source.label",
}

# === 1. Описание столбцов CSV в файле ===
csv_columns_description = {
    "ref_area.label": "Название страны (используем для определения country_id в CountryModel).",
    "source.label": "Источник данных (заполняет source_name в MetricModel).",
    "indicator.label": "Название метрики (MetricModel.name / slug).",
    "sex.label": "Пол ('Total', 'Male', 'Female' и т.д.) — можно добавить в add_info.",
    "classif1.label": "Первый классификатор (например, профессия или категория) — сохраняем в add_info.",
    "classif2.label": "Второй классификатор, часто единица измерения — идёт в MetricModel.unit_format.",
    "time": "Год (или период) — используется для MetricPeriodModel.period_year.",
    "obs_value": "Значение метрики — сохраняется в MetricDataModel.value_float.",
    "obs_status.label": "Статус наблюдения (например, 'Break in series') — add_info['obs_status'].",
    "note_indicator.label": "Примечание к показателю — add_info['note_indicator'].",
    "note_source.label": "Описание источника — add_info['note_source'] или MetricModel.source_url.",
}


# === 2. Сопоставление стран ===
COUNTRY_MAP = {
    "bolivia (plurinational state of)": ["Bolivia"],
    "brunei darussalam": ["Brunei"],
    "côte d'ivoire": ["Ivory Coast"],
    "hong kong, china": ["Hong Kong"],
    "lao people's democratic republic": ["Laos"],
    "macao, china": ["Macao"],
    "occupied palestinian territory": ["Palestine"],
    "republic of korea": ["South Korea"],
    "republic of moldova": ["Moldova"],
    "russian federation": ["Russia"],
    "tanzania, united republic of": ["Tanzania"],
    "united kingdom of great britain and northern ireland": ["Great Britain", "Ireland"],
    "united states of america": ["USA"],
    "venezuela (bolivarian republic of)": ["Venezuela"],
    "viet nam": ["Vietnam"],
}


# === Проверка структуры CSV ===
def validate_csv_structure(header: Union[Sequence[str], List[str]]) -> None:
    """Проверяет, что все нужные колонки есть в CSV.
    Если не хватает — бросает ValueError с описанием.
    """

    header_set = set(col.strip() for col in header)
    missing = REQUIRED_COLUMNS - header_set
    extra = header_set - REQUIRED_COLUMNS

    if missing:
        msg = f"❌ В CSV отсутствуют обязательные колонки: {', '.join(sorted(missing))}"
        logger.error(msg)
        raise ValueError(msg)

    if extra:
        logger.warning(f"⚠️ В CSV найдены лишние колонки (они будут проигнорированы): {', '.join(sorted(extra))}")

    logger.info("✅ Структура CSV проверена — все нужные поля присутствуют.")


# === Основная логика импорта ===
async def import_csv(file_path: Path, batch_size: int = 50):
    """Импорт данных метрик из CSV в БД.

    Основная логика:
    1. Сопоставляем страну -> country_id
    2. Создаём (или берём) метрику MetricModel
    3. Создаём (или берём) период MetricPeriodModel
    4. Добавляем запись MetricDataModel
    """

    # Создаю асинхронную сессию
    async with AsyncSessionLocal() as async_session:

        # Кэш
        metric_cache: Dict[str, MetricInfoModel] = {}
        series_cache: Dict[str, MetricSeriesModel] = {}
        period_cache: Dict[str, MetricPeriodModel] = {}
        country_cache: Dict[str, int] = {}

        buffer: List[MetricDataModel] = []  # Буфер для batch insert
        total_inserted = 0

        # Открываю CSV файл
        with open(file_path, encoding="utf-8") as f:

            # Читаем первую строку (заголовки) и чистим их
            raw_header = f.readline().strip().split(",")
            header = [col.strip().replace("\ufeff", "").replace('"', "").replace("'", "") for col in raw_header]

            # === Проверка заголовков ===
            validate_csv_structure(header)

            # Переходим в начало файла и создаём DictReader с чистыми заголовками
            f.seek(0)
            reader = csv.DictReader(f, fieldnames=header)
            next(reader)  # пропускаем первую строку-заголовок (уже использована)

            # Прохожусь по строкам файла
            for idx, row in enumerate(reader, 1):
                # logger.info(f"\n🔹 {idx}. {row['indicator.label']} — {row['ref_area.label']}")

                # === Определяем страну ===
                raw_country = row["ref_area.label"].strip().lower()
                country_names = COUNTRY_MAP.get(raw_country, [row["ref_area.label"].strip()])

                # Прохожусь по странам с особенностями
                for country_name in country_names:

                    # Кэш стран
                    if country_name in country_cache:
                        country_id = country_cache[country_name]
                    else:
                        country = await CountryModel.get(async_session, CountryGetDTO(name_eng=country_name))
                        if not country:
                            logger.warning(f"⚠️ Страна '{country_name}' не найдена — пропуск.")
                            continue
                        country_id = cast(int, country.id)
                        country_cache[country_name] = country_id

                    # === Создаю метрику ===
                    slug = row["indicator.label"].lower().replace(" ", "_").strip()
                    unique_key_metric = slug

                    # Кэш метрик
                    metric = metric_cache.get(unique_key_metric)
                    if not metric:
                        metric_dto_create = MetricInfoCreateDTO(
                            slug=slug,
                            name="Средний ежемесячный заработок работников по полу и роду занятий",
                            description="Средний ежемесячный заработок работников по полу и роду занятий",
                            category=CategoryMetricEnum.ECONOMY,
                            source_name="ILOSTAT data explorer",
                            source_url="https://rshiny.ilo.org/dataexplorer06/?lang=en&segment=indicator&id=EAR_4MTH_SEX_OCU_CUR_NB_A",
                            type_data=TypeDataEnum.FLOAT,
                            is_active=True,
                            add_info=None,
                        )
                        metric = await MetricInfoModel.get_or_create(async_session, metric_dto_create)
                        metric_id = cast(int, metric.id)
                        metric_cache[unique_key_metric] = metric

                    # === Создаю серию ===
                    gender = row["sex.label"]
                    unit = row["classif2.label"].strip()
                    professions = row["classif1.label"]
                    unique_key_series = f"{metric_id} {gender} {unit} {professions}"

                    # Кэш метрик
                    series = series_cache.get(unique_key_series)
                    if not series:
                        series_dto_create = MetricSeriesCreateDTO(
                            metric_id=metric_id,
                            is_active=True,
                            add_info={"unit": unit, "gender": gender, "professions": professions},
                        )
                        series = await MetricSeriesModel.get_or_create(async_session, series_dto_create)
                        series_id = cast(int, series.id)
                        series_cache[unique_key_series] = series

                    # === Создаю период для метрики===
                    year = int(row["time"])
                    unique_key_period = f"{metric_id}_{series_id}_{year}"

                    # Кэш периода
                    period = period_cache.get(unique_key_period)
                    if not period:
                        period_dto_create = MetricPeriodCreateDTO(
                            series_id=series_id,
                            period_type=PeriodTypeEnum.YEARLY,
                            period_year=year,
                            add_info=None,
                        )
                        period = await MetricPeriodModel.get_or_create(async_session, period_dto_create)
                        period_id = cast(int, period.id)
                        period_cache[unique_key_period] = period

                    # === Создаю значение для метрики ===
                    try:
                        value = float(row["obs_value"]) if row["obs_value"] else None
                    except ValueError:
                        logger.warning(f"⚠️ Некорректное значение obs_value: {row['obs_value']}")
                        continue

                    buffer.append(
                        MetricDataModel(
                            series_id=series_id,
                            period_id=period_id,
                            country_id=country_id,
                            value_float=value,
                            add_info={
                                "obs_status": row["obs_status.label"],
                                "note_classif": row["note_classif.label"],
                                "note_indicator": row["note_indicator.label"],
                                "note_source": row["note_source.label"],
                            },
                        )
                    )

                    # === Массовая вставка ===
                    if len(buffer) >= batch_size:
                        async_session.add_all(buffer)
                        await async_session.commit()
                        total_inserted += len(buffer)
                        logger.info(f"💾 Массовая загрузка — {total_inserted} записей")
                        buffer.clear()

        # Финальный commit оставшихся записей
        if buffer:
            async_session.add_all(buffer)
            await async_session.commit()
            total_inserted += len(buffer)
            logger.info(f"💾 Финальный commit — {total_inserted} записей")

        logger.info(f"\n✅ Импорт завершён. Всего добавлено: {total_inserted} записей.")


if __name__ == "__main__":
    asyncio.run(import_csv(Path("data/EAR_4MTH_SEX_OCU_CUR_NB_A-filtered-2025-11-01.csv")))
