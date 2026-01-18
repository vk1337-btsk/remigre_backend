# etl/fill_labout_comes_by_sex.py
"""
Заполняет метрики по
Labour market outcomes of immigrants - Employment rates by educational attainment
сайт: https://data-explorer.oecd.org/vis?lc=en&df[ds]=DisseminateFinalDMZ&df[id]=DSD_MIG%40DF_MIG_NUP_SEX&df[ag]=OECD.ELS.IMD&df[vs]=1.0&dq=..A.UNE_RATE%2BLF_RATE%2BEMP_WAP....&pd=2000%2C2024&to[TIME_PERIOD]=false
файл: OECD.ELS.IMD,DSD_MIG@DF_MIG_NUP_SEX,1.0+..A.UNE_RATE+LF_RATE+EMP_WAP....

Импорт данных OECD миграции в БД.
Перед загрузкой — сопоставление стран с CountryModel.
"""

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
    "STRUCTURE",
    "STRUCTURE_ID",
    "STRUCTURE_NAME",
    "ACTION",
    "REF_AREA",
    "Reference area",
    "CITIZENSHIP",
    "Citizenship",
    "FREQ",
    "Frequency of observation",
    "MEASURE",
    "Measure",
    "SEX",
    "Sex",
    "BIRTH_PLACE",
    "Place of birth",
    "EDUCATION_LEV",
    "Education level",
    "UNIT_MEASURE",
    "Unit of measure",
    "TIME_PERIOD",
    "Time period",
    "OBS_VALUE",
    "Observation value",
    "OBS_STATUS",
    "Observation status",
    "UNIT_MULT",
    "Unit multiplier",
    "DECIMALS",
    "Decimals",
}

# Маппинг кодов в CSV -> список ISO Alpha-3
COUNTRY_MAP = {
    "EU27_2020": [
        "AUT",
        "BEL",
        "BGR",
        "HRV",
        "CYP",
        "CZE",
        "DNK",
        "EST",
        "FIN",
        "FRA",
        "DEU",
        "GRC",
        "HUN",
        "IRL",
        "ITA",
        "LVA",
        "LTU",
        "LUX",
        "MLT",
        "NLD",
        "POL",
        "PRT",
        "ROU",
        "SVK",
        "SVN",
        "ESP",
        "SWE",
    ],
    "AUS": ["AUS"],
}


# ============================================================
#                 ОСНОВНОЙ ИМПОРТ CAR
# ============================================================
async def import_csv(session: AsyncSession, file_path: Path, batch_size: int = 50):
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
        raw_header = f.readline().strip().split(",")
        header = [col.strip().replace("\ufeff", "").replace('"', "").replace("'", "") for col in raw_header]

        # === Проверка заголовков ===
        validate_csv_structure(header, REQUIRED_COLUMNS)

        # Переходим в начало файла и создаём DictReader с чистыми заголовками
        f.seek(0)
        reader = csv.DictReader(f, fieldnames=header)
        next(reader)  # пропускаем первую строку-заголовок (уже использована)

        # Прохожусь по строкам файла
        for row in reader:

            # --- Получаем список стран ---
            country_from_file = row["REF_AREA"].strip()
            country_iso_alpha3_codes = COUNTRY_MAP.get(country_from_file, [country_from_file])

            # Прохожусь по странам с особенностями
            for country_code in country_iso_alpha3_codes:

                # === Определяем страну ===
                if country_code in country_cache:
                    country_id = country_cache[country_code]
                else:
                    country_obj = await CountryModel.get(session, CountryGetDTO(iso_alpha_3=country_code))
                    if not country_obj:
                        logger.warning(f"⚠️ Страна '{country_code}' не найдена — пропуск.")
                        continue
                    country_id = cast(int, country_obj.id)
                    country_cache[country_code] = country_id

                # === Создаю метрику: определяю основные поля и вызываю метод get_or_create_metric_cached ===
                slug = row["STRUCTURE_NAME"].lower().replace(" ", "_").strip()
                unique_key_metric = slug
                name = row["STRUCTURE_NAME"]
                description = row["STRUCTURE_NAME"]
                category = CategoryMetricEnum.ECONOMY
                source_name = "OECD Data Explorer"
                source_url = "https://data-explorer.oecd.org/vis?lc=en&df[ds]=DisseminateFinalDMZ&df[id]=DSD_MIG%40DF_MIG_NUP_SEX&df[ag]=OECD.ELS.IMD&df[vs]=1.0&dq=..A.UNE_RATE%2BLF_RATE%2BEMP_WAP....&pd=2000%2C2024&to[TIME_PERIOD]=false"
                type_data = TypeDataEnum.FLOAT
                add_info = {
                    "citizenship": row["Citizenship"],
                    "frequency_of_observation": row["Frequency of observation"],
                    "education_level": row["Education level"],
                }

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
                gender = row["Sex"]
                unit = row["Unit multiplier"].lower().strip()
                place_of_birth = row["Place of birth"].lower().strip()
                unit_of_measure = row["Unit of measure"]
                measure = row["Measure"]
                unique_key_series = f"{metric_id} {gender} {unit} {place_of_birth} {unit_of_measure} {measure}"
                add_info = {
                    "unit": unit,
                    "gender": gender,
                    "place_of_birth": place_of_birth,
                    "unit_of_measure": unit_of_measure,
                    "measure": measure,
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
                year = int(row["TIME_PERIOD"])
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
                    value = float(row["OBS_VALUE"].strip()) if row["OBS_VALUE"].strip() else None
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
                    # logger.info(f"💾 Массовая загрузка — {total_inserted} записей")
                    buffer.clear()

    # Финальный commit оставшихся записей
    if buffer:
        session.add_all(buffer)
        await session.commit()
        total_inserted += len(buffer)
        # logger.info(f"💾 Финальный commit — {total_inserted} записей")

    logger.info(f"\n✅ Импорт завершён. Всего добавлено: {total_inserted} записей.")


# ================= Main =================
async def main(mode: Literal["check", "import"]):

    file_path = Path("data/OECD.ELS.IMD,DSD_MIG@DF_MIG_NUP_SEX,1.0+..A.UNE_RATE+LF_RATE+EMP_WAP.....csv")

    async with AsyncSessionLocal() as session:
        if mode == "check":
            df = pd.read_csv(file_path)
            values = df["REF_AREA"].tolist()
            await compare_country_list_by_column(
                session=session,
                list_string=values,
                column_name="iso_alpha_3",
            )
            return

        elif mode == "import":
            await import_csv(session=session, file_path=file_path)
            return
