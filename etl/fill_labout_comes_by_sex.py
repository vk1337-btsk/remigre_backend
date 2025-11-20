# etl/fill_labout_comes_by_sex.py
"""
Заполняет метрики по
Labour market outcomes of immigrants - Employment, unemployment, and participation rates by sex
сайт: https://data-explorer.oecd.org/vis?lc=en&df[ds]=DisseminateFinalDMZ&df[id]=DSD_MIG%40DF_MIG_NUP_SEX&df[ag]=OECD.ELS.IMD&df[vs]=1.0&dq=..A.EMP_WAP....&pd=2020%2C2024&to[TIME_PERIOD]=false
файл: OECD.ELS.IMD,DSD_MIG@DF_MIG_NUP_SEX,1.0+..A.EMP_WAP....

Импорт данных OECD миграции в БД.
Перед загрузкой — сопоставление стран с CountryModel.
"""

import asyncio
import csv
from pathlib import Path
from typing import Dict, List, Literal, Sequence, Union, cast

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config.logging import setup_logger_to_file
from src.core.database.db_config import AsyncSessionLocal
from src.core.utils.country_companator import compare_country_list_by_column
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
#                    Функции
# ============================================================
def validate_csv_structure(header: Union[Sequence[str], List[str]]) -> None:
    """Проверяет, что все нужные колонки есть в CSV. Если не хватает — бросает ValueError с описанием."""

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


async def get_or_create_metric_cached(
    cache: Dict[str, MetricInfoModel],
    unique_key: str,
    session: AsyncSession,
    slug: str,
    name: str,
    description: str,
    category: CategoryMetricEnum,
    source_name: str,
    source_url: str,
    type_data: TypeDataEnum,
    add_info: dict,
) -> MetricInfoModel:

    if unique_key in cache:
        return cache[unique_key]

    metric = await MetricInfoModel.get_or_create(
        session,
        MetricInfoCreateDTO(
            slug=slug,
            name=name,
            description=description,
            category=category,
            source_name=source_name,
            source_url=source_url,
            type_data=type_data,
            add_info=add_info,
            is_active=True,
        ),
    )
    cache[unique_key] = metric
    return metric


async def get_or_create_series_cached(
    cache: Dict[str, MetricSeriesModel],
    unique_key: str,
    session: AsyncSession,
    metric_id: int,
    add_info: dict,
) -> MetricSeriesModel:

    if unique_key in cache:
        return cache[unique_key]

    series = await MetricSeriesModel.get_or_create(
        session,
        MetricSeriesCreateDTO(metric_id=metric_id, add_info=add_info, is_active=True),
    )
    cache[unique_key] = series
    return series


async def get_or_create_period_cached(
    cache: Dict[str, MetricPeriodModel],
    unique_key: str,
    session: AsyncSession,
    series_id: int,
    period_type: PeriodTypeEnum,
    year: int,
) -> MetricPeriodModel:
    if unique_key in cache:
        return cache[unique_key]

    period = await MetricPeriodModel.get_or_create(
        session,
        MetricPeriodCreateDTO(
            series_id=series_id,
            period_type=period_type,
            period_year=year,
            add_info=None,
        ),
    )
    cache[unique_key] = period
    return period


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
        validate_csv_structure(header)

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
                source_url = "https://data-explorer.oecd.org/vis?lc=en&df[ds]=DisseminateFinalDMZ&df[id]=DSD_MIG%40DF_MIG_NUP_SEX&df[ag]=OECD.ELS.IMD&df[vs]=1.0&dq=..A.EMP_WAP....&pd=2020%2C2024&to[TIME_PERIOD]=false"
                type_data = TypeDataEnum.FLOAT
                add_info = {
                    "citizenship": row["Citizenship"],
                    "frequency_of_observation": row["Frequency of observation"],
                    "measure": row["Measure"],
                    "education_level": row["Education level"],
                    "unit_of_measure": row["Unit of measure"],
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
                unique_key_series = f"{metric_id} {gender} {unit} {place_of_birth}"
                add_info = {
                    "gender": gender,
                    "unit": unit,
                    "place_of_birth": place_of_birth,
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
async def main(file_path: Path, mode: Literal["check", "import"]):

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


if __name__ == "__main__":
    raise RuntimeError("Этот скрипт нельзя запускать без причин!")

    path = Path("data/OECD.ELS.IMD,DSD_MIG@DF_MIG_NUP_SEX,1.0+..A.EMP_WAP.....csv")
    asyncio.run(main(file_path=path, mode="import"))
