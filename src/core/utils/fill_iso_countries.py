import asyncio
import csv
import logging

# Импорт зависимых моделей, чтобы SQLAlchemy смогла построить все связи
from src.ms_metric.models.data import MetricDataModel
from src.ms_location.models.city import CityModel
from src.ms_location.models.region import RegionModel

from src.core.database.db_config import get_async_session
from src.ms_location.dto import CountryGetDTO, CountryUpdateDTO
from src.ms_location.models.country import CountryModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CSV_FILE = "country-codes.csv"


async def main():
    # Чтение CSV и формирование словаря по ISO Alpha-2
    iso_map = {}
    with open(CSV_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            alpha2 = row.get("ISO3166-1-Alpha-2")
            alpha3 = row.get("ISO3166-1-Alpha-3")
            numeric = row.get("ISO3166-1-numeric")
            if alpha2:
                iso_map[alpha2] = {"iso_alpha_3": alpha3, "iso_digits": numeric}

    async for session in get_async_session():
        # Проходим по всем странам в БД
        for alpha2, codes in iso_map.items():
            dto_get = CountryGetDTO(iso_alpha_2=alpha2)

            # Передаем dto_options=None, чтобы не загружать связи
            country = await CountryModel.get(session, dto_get, dto_options=None)
            if not country:
                logger.warning(f"Страна с ISO Alpha-2 {alpha2} не найдена в БД")
                continue

            dto_update = CountryUpdateDTO(
                iso_alpha_3=codes["iso_alpha_3"],
                iso_digits=codes["iso_digits"],
            )
            await CountryModel.update(session, dto_get, dto_update)
            logger.info(f"Обновлено: {alpha2} → {codes['iso_alpha_3']}, {codes['iso_digits']}")

    logger.info("Обновление завершено!")


if __name__ == "__main__":
    asyncio.run(main())
