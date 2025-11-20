"""
Скрипт заполнения таблицы data_professions из файла
Скачал данные отсюда:  https://ilostat.ilo.org/methods/concepts-and-definitions/classification-occupation/
Файл в data: ISCO-08 EN Structure and definitions.xlsx
Title EN -> name, name_eng
Остальные колонки -> add_info (JSONB)
"""

import asyncio
from pathlib import Path

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.db_config import AsyncSessionLocal
from src.ms_data_directory.models.professions import ProfessionsModel


# Путь к Excel-файлу (можно сделать через аргументы командной строки, если нужно)
EXCEL_PATH = Path("data/ISCO-08 EN Structure and definitions.xlsx")
SHEET_NAME = "ISCO-08 EN Struct and defin"  # имя листа из файла


async def load_professions(session: AsyncSession) -> None:
    """Загружает данные из Excel в таблицу data_professions.

    Title EN -> name, name_eng
    Остальные колонки -> add_info
    """

    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"Файл не найден: {EXCEL_PATH.resolve()}")

    # Читаем Excel
    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)

    # Оставляем строки, где есть Title EN
    if "Title EN" not in df.columns:
        raise ValueError("В Excel-файле нет колонки 'Title EN'")

    df = df[df["Title EN"].notna()]

    objects: list[ProfessionsModel] = []

    for _, row in df.iterrows():
        title_en = str(row["Title EN"]).strip()

        # Собираем add_info из всех остальных колонок, кроме Title EN
        add_info: dict[str, object] = {}
        for col in df.columns:
            if col == "Title EN":
                continue

            value = row[col]

            # пропускаем NaN/None
            if pd.isna(value):
                continue

            # pandas может отдавать numpy-типы — приводим к обычным питоновским
            if hasattr(value, "item"):
                try:
                    value = value.item()
                except Exception:
                    pass

            add_info[col] = value

        obj = ProfessionsModel(name=title_en, name_eng=title_en, add_info=add_info)
        objects.append(obj)

    session.add_all(objects)
    await session.commit()
    print(f"Загружено записей: {len(objects)}")


async def main() -> None:
    # Берём уже настроенную фабрику сессий из db_config
    async with AsyncSessionLocal() as session:
        await load_professions(session)


if __name__ == "__main__":
    asyncio.run(main())
