"""
Скрипт для заполнения БД данными о средней месячной ЗП по полу и роду деятельности
Скачал данные отсюда: https://rshiny.ilo.org/dataexplorer06/?lang=en&segment=indicator&id=EAR_4MTH_SEX_OCU_CUR_NB_A
Файл в data: EAR_4MTH_SEX_OCU_CUR_NB_A-filtered-2025-11-20
"""

import asyncio
import csv
from pathlib import Path
from typing import Dict, List, Literal, cast

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from etl.utils import (
    compare_country_list_by_column,
    get_or_create_metric_cached,
    get_or_create_period_cached,
    get_or_create_series_cached,
    validate_csv_structure,
)
from src.core.config.logging import setup_logger_to_file
from src.core.database.database import AsyncSessionLocal
from src.ms_location.dto import CountryGetDTO
from src.ms_location.models import CountryModel
from src.ms_metric.enums import CategoryMetricEnum, PeriodTypeEnum, TypeDataEnum
from src.ms_metric.models import (
    MetricDataModel,
    MetricInfoModel,
    MetricPeriodModel,
    MetricSeriesModel,
)


logger = setup_logger_to_file()


# ============================================================
#                    CONFIG
# ============================================================
# Укажи требуемые колонки в CSV файле
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

# Маппинг кодов в CSV -> список
COUNTRY_MAP = {
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
}


# ============================================================
#                 ОСНОВНОЙ ИМПОРТ CAR
# ============================================================
async def import_csv(session: AsyncSession, file_path: Path, batch_size: int = 50, delimiter: str = ","):
    """Импорт данных метрик из CSV в БД.

    Основная логика:
    1. Сопоставляем страну
    2. Создаём (или берём) метрику MetricInfoModel
    3. Создаём (или берём) серию MetricSeriesModel
    4. Создаём (или берём) период MetricPeriodModel
    5. Добавляем запись MetricDataModel
    """

    # Кэш
    country_cache: Dict[str, int] = {}
    metric_cache: Dict[str, MetricInfoModel] = {}
    series_cache: Dict[str, MetricSeriesModel] = {}
    period_cache: Dict[str, MetricPeriodModel] = {}

    buffer: List[MetricDataModel] = []  # Буфер для batch insert
    total_inserted = 0

    # Открываю CSV файл
    with open(file_path, encoding="utf-8") as f:

        # Читаем первую строку (заголовки) и чистим их
        raw_header = f.readline().strip().split(delimiter)
        header = [col.strip().replace("\ufeff", "").replace('"', "").replace("'", "") for col in raw_header]

        # === Проверка заголовков ===
        validate_csv_structure(header, REQUIRED_COLUMNS)

        # Переходим в начало файла и создаём DictReader с чистыми заголовками
        f.seek(0)
        reader = csv.DictReader(f, fieldnames=header, delimiter=delimiter)
        next(reader)  # пропускаем первую строку-заголовок (уже использована)

        # Прохожусь по строкам файла
        for row in reader:

            # --- Получаем список стран ---
            country_from_file = row["ref_area.label"].strip()
            list_country_name_eng = COUNTRY_MAP.get(country_from_file, [country_from_file])

            # Прохожусь по странам с особенностями
            for country_name_eng in list_country_name_eng:

                # === Определяем страну ===
                if country_name_eng in country_cache:
                    country_id = country_cache[country_name_eng]
                else:
                    country_obj = await CountryModel.get(session, CountryGetDTO(name_eng=country_name_eng))
                    if not country_obj:
                        logger.warning(f"⚠️ Страна '{country_name_eng}' не найдена — пропуск.")
                        continue
                    country_id = cast(int, country_obj.id)
                    country_cache[country_name_eng] = country_id

                # === Создаю метрику: определяю основные поля и вызываю метод get_or_create_metric_cached ===
                slug = row["indicator.label"].lower().replace(" ", "_").strip()
                unique_key_metric = slug
                name = row["indicator.label"]
                description = None
                category = CategoryMetricEnum.ECONOMY
                source_name = "ILOSTAT"
                source_url = (
                    "https://rshiny.ilo.org/dataexplorer06/?lang=en&segment=indicator&id=EAR_4MTH_SEX_OCU_CUR_NB_A"
                )
                type_data = TypeDataEnum.FLOAT
                add_info = None

                metric = await get_or_create_metric_cached(
                    cache=metric_cache,
                    unique_key=unique_key_metric,
                    session=session,
                    slug=slug,
                    name=name,
                    description=description,
                    category=category,
                    source_name=source_name,
                    source_url=source_url,
                    type_data=type_data,
                    add_info=add_info,
                )
                metric_id = cast(int, metric.id)

                # === Создаю серию: определяю основные поля и вызываю метод get_or_create_series_cached ===
                gender = row["sex.label"]
                unit = row["classif2.label"].strip()
                profession = row["classif1.label"].strip()
                source = row["source.label"].strip()
                obs_status = row["obs_status.label"].strip()
                note_indicator = row["note_indicator.label"].strip()
                note_source = row["note_source.label"].strip()

                unique_key_series = (
                    f"{metric_id} {unit} {gender} {profession} {source} {obs_status} {note_indicator} {note_source}"
                )
                add_info = {
                    "unit": unit,
                    "gender": gender,
                    "profession": profession,
                    "source": source,
                    "obs_status": obs_status,
                    "note_indicator": note_indicator,
                    "note_source": note_source,
                }

                series = await get_or_create_series_cached(
                    cache=series_cache,
                    unique_key=unique_key_series,
                    session=session,
                    metric_id=metric_id,
                    add_info=add_info,
                )
                series_id = cast(int, series.id)

                # === Создаю период: определяю основные поля и вызываю метод get_or_create_period_cached ===
                year = int(row["time"])
                period_type = PeriodTypeEnum.YEARLY
                unique_key_period = f"{metric_id}_{series_id}_{year}"

                period = await get_or_create_period_cached(
                    cache=period_cache,
                    unique_key=unique_key_period,
                    session=session,
                    series_id=series_id,
                    period_type=period_type,
                    year=year,
                )
                period_id = cast(int, period.id)

                # === Создаю значение для метрики ===
                try:
                    value = float(row["obs_value"].strip().replace(",", ".")) if row["obs_value"].strip() else None
                except ValueError:
                    logger.warning(f"⚠️ Некорректное значение obs_value: {row['obs_value']}")
                    continue

                if value is None:
                    continue

                buffer.append(
                    MetricDataModel(
                        series_id=series_id,
                        period_id=period_id,
                        country_id=country_id,
                        value_float=value,
                        add_info=None,
                    )
                )

                # === Массовая вставка ===
                if len(buffer) >= batch_size:
                    session.add_all(buffer)
                    await session.commit()
                    total_inserted += len(buffer)
                    logger.info(f"💾 Массовая загрузка — {total_inserted} записей")
                    buffer.clear()

    # Финальный commit оставшихся записей
    if buffer:
        session.add_all(buffer)
        await session.commit()
        total_inserted += len(buffer)
        logger.info(f"💾 Финальный commit — {total_inserted} записей")

    logger.info(f"\n✅ Импорт завершён. Всего добавлено: {total_inserted} записей.")


# ================= Main =================
async def main(mode: Literal["check", "import"]):

    file_path = Path("data/EAR_4MTH_SEX_OCU_CUR_NB_A-filtered-2025-11-20-2.csv")

    async with AsyncSessionLocal() as session:
        if mode == "check":
            df = pd.read_csv(file_path, sep=",")
            values = df["ref_area.label"].tolist()
            await compare_country_list_by_column(
                session=session,
                list_string=values,
                column_name="name_eng",
                country_map=COUNTRY_MAP,
            )
            return

        elif mode == "import":
            await import_csv(session=session, file_path=file_path, batch_size=100, delimiter=";")
            return
