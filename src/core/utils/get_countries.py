import asyncio
import json
import logging
from pathlib import Path

import requests
from sqlalchemy.ext.asyncio import AsyncSession

import src.core.database.models_init
from src.core.database import AsyncSessionLocal
from src.ms_location.dto.country_dto import CountryCreateDTO
from src.ms_location.models.country import CountryModel


logger = logging.getLogger(__name__)


def fetch_countries(api_key: str, url: str, output_file: Path, language: str) -> None:
    """Получает список стран из API Oxilor и сохраняет в JSON-файл."""

    headers = {"Authorization": f"Bearer {api_key}", "Accept-Language": language}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        countries_data = response.json()

        output_file.write_text(json.dumps(countries_data, ensure_ascii=False, indent=2), encoding="utf-8")

        logger.debug(f"✅ Список стран ({language}) сохранён в {output_file}")
    except requests.exceptions.HTTPError as http_err:
        logger.debug(f"❌ HTTP ошибка: {http_err}")
    except Exception as err:
        logger.debug(f"❌ Ошибка при получении стран ({language}): {err}")


async def load_countries_from_json(session: AsyncSession, path_ru: Path, path_en: Path):
    """Загружает в БД скачанные страны из json файла"""

    with path_en.open(encoding="utf-8") as f_en, path_ru.open(encoding="utf-8") as f_ru:
        data_en = {entry["id"]: entry for entry in json.load(f_en)}
        data_ru = {entry["id"]: entry for entry in json.load(f_ru)}

    created = 0

    for country_id, ru_item in data_ru.items():
        en_item = data_en.get(country_id)
        if not en_item:
            continue

        try:
            dto = CountryCreateDTO(
                name=ru_item["name"],
                name_eng=en_item["name"],
                iso_code=ru_item["countryCode"],
                latitude=float(ru_item["latitude"]),
                longitude=float(ru_item["longitude"]),
                population=int(ru_item["population"]) if ru_item.get("population") else None,
                timezone=ru_item.get("timezone") or None,
                description=ru_item.get("id"),
            )

            await CountryModel.create(session, dto)
            created += 1
        except Exception as e:
            logger.debug(f"❌ Ошибка при обработке страны {ru_item['name']} ({country_id}): {e}")

    await session.commit()
    logger.debug(f"✅ Загружено стран: {created}")


async def run_import():
    """Запуск скрипта скачивания и сохранения стран в БД"""

    API_KEY = "nWSTp2jmGI9JebcjVLa_YKncLea_Cy"
    URL = "https://data-api.oxilor.com/rest/countries"
    path_ru = Path("countries.json")
    path_en = Path("countries_en.json")

    # Скачиваем данные
    fetch_countries(API_KEY, URL, path_en, "en")
    fetch_countries(API_KEY, URL, path_ru, "ru")

    # Загружаем в БД
    async with AsyncSessionLocal() as session:
        await load_countries_from_json(session, path_ru, path_en)


if __name__ == "__main__":
    asyncio.run(run_import())
