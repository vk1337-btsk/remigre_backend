# check_missing_countries_async.py

# NOTE: что-то старое


import asyncio
import csv
from pathlib import Path
from typing import Dict, Set

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.database import AsyncSessionLocal  # ваш AsyncSession


CSV_PATH = Path("data/EAR_4MTH_SEX_OCU_CUR_NB_A-filtered-2025-11-01.csv")

# Маппинг: ключ — как в CSV (lower), значение — как хранится в БД (точно так, как в loc_country.name_eng)
CSV_TO_DB_NAME: Dict[str, str] = {
    "bolivia (plurinational state of)": "Bolivia",
    "brunei darussalam": "Brunei",
    "côte d'ivoire": "Ivory Coast",
    "hong kong, china": "Hong Kong",
    "lao people's democratic republic": "Laos",
    "macao, china": "Macao",
    "occupied palestinian territory": "Palestine",
    "republic of korea": "South Korea",
    "republic of moldova": "Moldova",
    "russian federation": "Russia",
    "tanzania, united republic of": "Tanzania",
    "united kingdom of great britain and northern ireland": "Great Britain и Ireland",
    "united states of america": "USA",
    "venezuela (bolivarian republic of)": "Venezuela",
    "viet nam": "Vietnam",
}


def _find_country_key(fieldnames) -> str:
    """Найти ключ колонки страны в заголовке CSV (с учётом BOM и кавычек)."""
    for raw in fieldnames:
        key = (raw or "").replace("\ufeff", "").strip().strip('"').strip()
        if key == "ref_area.label":
            return raw  # вернуть исходный ключ, чтобы им доставать из row
    raise KeyError("Колонка 'ref_area.label' не найдена в CSV.")


def csv_countries(csv_path: Path) -> Set[str]:
    """
    Возвращает множество НОРМАЛИЗОВАННЫХ названий стран из CSV,
    уже после применения маппинга к форме, которая хранится в БД.
    """
    result: Set[str] = set()
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        country_key = _find_country_key(reader.fieldnames or [])
        for row in reader:
            raw_val = (row.get(country_key) or "").strip()
            if not raw_val:
                continue
            csv_name_lower = raw_val.lower()
            mapped = CSV_TO_DB_NAME.get(csv_name_lower, raw_val)  # если нет в маппинге — оставляем как есть
            result.add(mapped.strip())
    return result


async def db_countries(session: AsyncSession) -> Set[str]:
    """
    Возвращает множество стран из БД в том виде, как они там хранятся (name_eng).
    """
    res = await session.execute(text("SELECT name_eng FROM loc_country"))
    return {(r[0] or "").strip() for r in res.fetchall() if r[0]}


async def main():
    csv_set = csv_countries(CSV_PATH)  # уже в «DB-представлении»
    async with AsyncSessionLocal() as session:
        db_set = await db_countries(session)  # как в БД

    # Для сравнения используем lower(), но печатать будем «как есть»
    csv_lower = {x.lower() for x in csv_set}
    db_lower = {x.lower() for x in db_set}

    missing_in_db_lower = csv_lower - db_lower  # есть в CSV, нет в БД
    missing_in_csv_lower = db_lower - csv_lower  # есть в БД, нет в CSV

    # Восстановим «красивые» версии для печати
    missing_in_db = sorted([x for x in csv_set if x.lower() in missing_in_db_lower])
    missing_in_csv = sorted([x for x in db_set if x.lower() in missing_in_csv_lower])

    print(f"В CSV (после маппинга): {len(csv_set)} | В БД: {len(db_set)}")
    print(f"Нет в БД (но есть в CSV): {len(missing_in_db)}")
    for c in missing_in_db:
        print(f"  - {c}")

    print(f"\nНет в CSV (но есть в БД): {len(missing_in_csv)}")
    for c in missing_in_csv:
        print(f"  - {c}")

    # Дополнительно: покажем, какие исходные CSV-имена были замапплены (для проверки)
    # и какие CSV-имена НЕ покрыты маппингом и отсутствуют в БД (чтобы расширить словарь).
    # Это удобно при первичном запуске и можно закомментировать позже.
    _show_mapping_diagnostics()


def _show_mapping_diagnostics():
    """Небольшой отчёт по самому маппингу: что маппится и что возможно ещё стоит добавить."""
    try:
        with CSV_PATH.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            country_key = _find_country_key(reader.fieldnames or [])
            original_csv_names = []
            for row in reader:
                raw_val = (row.get(country_key) or "").strip()
                if raw_val:
                    original_csv_names.append(raw_val)
    except Exception:
        return

    original_unique = sorted(set(original_csv_names), key=str.lower)
    print("\n[Диагностика маппинга]")
    mapped_pairs = []
    unmapped = []
    for raw in original_unique:
        key = raw.lower()
        if key in CSV_TO_DB_NAME:
            mapped_pairs.append((raw, CSV_TO_DB_NAME[key]))
        else:
            unmapped.append(raw)

    if mapped_pairs:
        print("Замаппленные значения (CSV -> БД):")
        for a, b in mapped_pairs:
            print(f"  {a}  ->  {b}")

    if unmapped:
        print("\nCSV-значения без явного маппинга (оставлены как есть):")
        # Показываем только первые 50, чтобы не засорять вывод
        for val in unmapped[:50]:
            print(f"  {val}")
        if len(unmapped) > 50:
            print(f"  ... и ещё {len(unmapped) - 50} шт.")


if __name__ == "__main__":
    asyncio.run(main())
