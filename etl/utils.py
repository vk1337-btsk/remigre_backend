# etl/utils.py
"""
Набор функций для загрузки данных в БД
"""

from typing import Any, Dict, Iterable, List, Optional, Sequence, Union, cast
import unicodedata

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config.logging import setup_logger_to_file
from src.ms_location.models import CountryModel
from src.ms_metric.dto import (
    MetricInfoCreateDTO,
    MetricPeriodCreateDTO,
    MetricSeriesCreateDTO,
)
from src.ms_metric.enums import CategoryMetricEnum, PeriodTypeEnum, TypeDataEnum
from src.ms_metric.models import MetricInfoModel, MetricPeriodModel, MetricSeriesModel


logger = setup_logger_to_file()


def validate_csv_structure(header: Union[Sequence[str], List[str]], required_coplumns: set) -> None:
    """Проверяет, что все нужные колонки есть в CSV. Если не хватает — бросает ValueError с описанием."""

    header_set = set(col.strip() for col in header)
    missing = required_coplumns - header_set
    extra = header_set - required_coplumns

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
    category: CategoryMetricEnum,
    source_name: str,
    source_url: str,
    type_data: TypeDataEnum,
    description: Optional[str] = None,
    add_info: Optional[dict] = None,
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


def to_dict(c: CountryModel) -> Dict[str, Any]:
    return {
        "id": c.id,
        "name": c.name,
        "name_eng": c.name_eng,
        "iso_alpha_2": c.iso_alpha_2,
        "iso_alpha_3": c.iso_alpha_3,
        "iso_digits": c.iso_digits,
        "is_active": c.is_active,
    }


async def compare_country_list_by_column(
    session: AsyncSession,
    list_string: Iterable[str],
    column_name: str,
    active_only: bool = True,
    compare_db_all: bool = True,
    country_map: Optional[dict[str, list[str]]] = None,
) -> None:
    """
    Универсальное сравнение списка стран с БД через country_map.
    Сравнение производится без нормализации, с учётом алиасов из country_map.

    Args:
        session (AsyncSession): активная сессия SQLAlchemy
        list_string (Iterable[str]): список названий стран из файла
        column_name (str): колонка модели CountryModel, по которой сравниваем
        active_only (bool): учитывать только активные страны
        compare_db_all (bool): показывать страны из БД, которых нет в списке
        country_map (dict[str, list[str]]): ключи = название из файла, значения = список названий в БД
    """

    logger.info("\n====== СООТНЕСЕНИЕ СТРАН - СТАРТ ======")

    # --- Проверка колонки ---
    column_attr = getattr(CountryModel, column_name, None)
    if column_attr is None:
        raise ValueError(f"Column '{column_name}' not found in CountryModel")

    # --- Очистка входных данных (удаление дубликатов + сортировка) ---
    seen = set()
    for val in list_string:
        if val is None:
            continue
        s = str(val).strip().lower()
        if not s or s in seen:
            continue
        seen.add(s)

    list_string_cleaned: list[str] = sorted(list(seen))  # Список сортированный уникальных названий из файла

    if not list_string_cleaned:
        return

    # logger.info(f"{list_string_cleaned=}")
    # logger.info(f"{column_name=}")
    # logger.info(f"{country_map=}")

    # --- Запрос в БД для получения всех значений по колонке ---
    column_attr = getattr(CountryModel, column_name)
    name_eng_attr = getattr(CountryModel, "name_eng")

    # Если column_attr == name_eng, выбираем только один раз
    if column_name == "name_eng":
        stmt = select(column_attr)
    else:
        stmt = select(column_attr, name_eng_attr)

    if active_only:
        stmt = stmt.where(CountryModel.is_active.is_(True))

    result = await session.execute(stmt)

    # Получаем список
    if column_name == "name_eng":
        # если сравниваем по name_eng, достаём только её
        list_names_from_db = [el.lower() for el in result.scalars().all()]
    else:
        # result.fetchall() возвращает список кортежей (column_attr, name_eng)
        # сравнивать будем по column_attr
        list_names_from_db = [(el[0].lower(), el[1]) for el in result.fetchall()]  # lower только для сравнения

    # --- Построение списка для поиска в БД с учётом country_map ---
    country_map = country_map or {}
    list_names_from_file_and_map = []
    for item in list_string_cleaned:
        if item in country_map:
            list_names_from_file_and_map.extend([v.lower() for v in country_map[item]])
        else:
            list_names_from_file_and_map.append(item.lower())

    # --- Получаем список названий. которые есть БД, но нет в файле/карте ---
    if column_name == "name_eng":
        in_db_not_in_file = (
            set(list_names_from_db)
            - set(list_names_from_file_and_map)
            - {v.lower() for values in country_map.values() for v in values}
        )  # type: ignore
    else:
        # list_names_from_db = [(column_attr_value, name_eng)]
        in_db_not_in_file = (
            set(x[0].lower() for x in list_names_from_db)
            - set(list_names_from_file_and_map)
            - {v.lower() for values in country_map.values() for v in values}
        )

    # ---  Получаем список названий. которые есть в файле + карте, но нет в БД ---
    if column_name == "name_eng":
        in_file_not_in_db = (
            set(list_names_from_file_and_map) - set(list_names_from_db) - {el.lower() for el in country_map.keys()}
        )
    else:
        in_file_not_in_db = (
            set(list_names_from_file_and_map)
            - set(x[0].lower() for x in list_names_from_db)
            - {el.lower() for el in country_map.keys()}
        )

    # --- Логи ---
    logger.info(f"\n{'='*35} Получено значений: {len(list_string_cleaned)}")
    # logger.info(f"{list_string_cleaned=}")

    logger.info(f"\n{'='*35} Нет в БД: {len(in_file_not_in_db)}")
    for el in in_file_not_in_db:
        logger.info(f"{el.title()}")

    logger.info(f"\n{'='*35} Есть в БД и нет списке: {len(in_db_not_in_file)}")
    for el in in_db_not_in_file:
        if column_name == "name_eng":
            logger.info(f"{el.title()}")
        else:
            # находим name_eng для этого значения
            name_eng = next((x[1] for x in list_names_from_db if x[0].lower() == el), None)
            logger.info(f"{name_eng} ({el})")

    logger.info("====== СООТНЕСЕНИЕ СТРАН - ФИНИШ ======")
