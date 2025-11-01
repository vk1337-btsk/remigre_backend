import asyncio
import json
import logging
from pathlib import Path

import httpx
from geoalchemy2.shape import from_shape
from shapely.geometry import shape

from src.core.database.db_config import AsyncSessionLocal
from src.ms_location.dto import CountryGetDTO
from src.ms_location.models.country import CountryModel
from src.ms_metric.models.data import MetricDataModel


# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)
log_file = Path("geo_status.json")


async def fetch_geojson(iso_alpha_3: str):
    url = f"https://raw.githubusercontent.com/johan/world.geo.json/refs/heads/master/countries/{iso_alpha_3}.geo.json"
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            r = await client.get(url)
            r.raise_for_status()
            geo_data = r.json()
            # geojson на top-level "FeatureCollection" с 1 feature
            if "features" in geo_data and geo_data["features"]:
                return geo_data["features"][0]["geometry"]
        except Exception as e:
            logger.warning(f"{iso_alpha_3}: Ошибка при получении геометрии - {e}")
    return None


async def main():
    statuses = {}

    async with AsyncSessionLocal() as session:
        # Получаем все страны без geometry
        result = await session.execute(CountryModel.__table__.select().where(CountryModel.geometry.is_(None)))
        countries = result.fetchall()

        for row in countries:
            country_id = row.id
            iso_alpha_3 = row.iso_alpha_3
            logger.info(f"Обработка {iso_alpha_3}...")

            geom_json = await fetch_geojson(iso_alpha_3)

            if geom_json:
                shapely_geom = shape(geom_json)

                # Получаем объект CountryModel через метод get
                country = await CountryModel.get(session, CountryGetDTO(iso_alpha_3=iso_alpha_3))
                if country:
                    country.geometry = from_shape(shapely_geom, srid=4326)
                    session.add(country)
                    await session.commit()
                    statuses[iso_alpha_3] = "success"
                    logger.info(f"{iso_alpha_3}: Геометрия успешно добавлена")
                else:
                    statuses[iso_alpha_3] = "not_found"
                    logger.warning(f"{iso_alpha_3}: Страна не найдена в БД")
            else:
                statuses[iso_alpha_3] = "fail"
                logger.warning(f"{iso_alpha_3}: Геометрия не найдена")

    # Логируем результаты в JSON
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(statuses, f, ensure_ascii=False, indent=2)

    logger.info("Обработка завершена")


if __name__ == "__main__":
    asyncio.run(main())
