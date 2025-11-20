# src/core/utils/country_comparator.py

from typing import Any, Dict, Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config.logging import setup_logger_to_file
from src.ms_location.models import CountryModel


logger = setup_logger_to_file()


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
) -> None:
    """Универсальное сравнение списка строк со странами в БД

    Args:
        session (AsyncSession): Активная сессия
        list_string (Iterable[str]): Список строк по которым соотносим страны из БД со странами из файла
        column_name (str): Название колонки в БД, по которой соотносим страны
        active_only (bool, optional): Ищем только активные. Defaults to True.
        compare_db_all (bool, optional): Вернуть ли записи из БД, которых нет в списке. Defaults to True.

    Raises:
        ValueError: Бросает ValueError, если колонка не найдена в модели.
    """

    logger.info("====== СООТНЕСЕНИЕ СТРАН - СТАРТ ======")

    # 1. Проверка существования колонки
    column_attr = getattr(CountryModel, column_name, None)
    if column_attr is None:
        raise ValueError(f"Column '{column_name}' not found in CountryModel")

    # --- 2. Нормализация входа (удаляем пустые и дубли, сохраняем порядок) ---
    cleaned = []
    seen = set()

    for val in list_string:
        if val is None:
            continue
        s = str(val).strip()
        if not s or s in seen:
            continue
        cleaned.append(s)
        seen.add(s)

    # Если вход пуст — быстро вернуть результат
    if not cleaned:
        return

    # 3. Приведение к нижнему регистру
    lowered_inputs = [s.lower() for s in cleaned]

    # 4. Получаем найденные строки
    stmt = select(CountryModel).where(func.lower(column_attr).in_(lowered_inputs))
    if active_only:
        stmt = stmt.where(CountryModel.is_active.is_(True))

    found = (await session.execute(stmt)).scalars().all()

    found_dicts = [to_dict(c) for c in found]

    # 5. Какие входные не найдены
    found_norms = {getattr(c, column_name).lower() for c in found if getattr(c, column_name)}
    input_missing = [s for s in cleaned if s.lower() not in found_norms]

    # 6. db_only — опционально
    db_only = []
    if compare_db_all:
        stmt_all = select(CountryModel)
        if active_only:
            stmt_all = stmt_all.where(CountryModel.is_active.is_(True))

        all_rows = (await session.execute(stmt_all)).scalars().all()

        cleaned_norm = {s.lower() for s in cleaned}

        for row in all_rows:
            val = getattr(row, column_name)
            if val is None or val.strip().lower() not in cleaned_norm:
                db_only.append(to_dict(row))

    result = {
        "input_original": cleaned,
        "matched": found_dicts,
        "input_missing": input_missing,
        "db_only": db_only,
    }
    logger.info(f"\nПолучено значений стран: {len(cleaned)}")
    logger.info(f"{cleaned}")

    logger.info(f"\nИз них отсутствует в БД: {len(input_missing)}")
    [logger.info(f"{el}") for el in input_missing]

    logger.info(f"\nИз них есть в БД, но нет в списке: {len(db_only)}")
    [logger.info(f"{el['name_eng']}") for el in db_only]

    logger.info("====== СООТНЕСЕНИЕ СТРАН - ФИНИШ ======")
