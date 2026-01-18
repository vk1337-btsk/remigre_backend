"""Скрипт заполняет таблицу городов по странам"""

import asyncio
import json
from pathlib import Path
from random import randint

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.database import AsyncSessionLocal
from src.core.database.models_init import *
from src.ms_location.dto.city_dto import CityCreateDTO


API_URL = "https://data-api.oxilor.com/rest/regions"
API_KEY = "nWSTp2jmGI9JebcjVLa_YKncLea_Cy"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Accept-Language": "en"}


async def fetch_and_save_cities(
    session: AsyncSession, country_id: int, country_name: str, api_country_code: str, api_country_id: int
):
    """
    Запрашивает все города по API для указанной страны и сохраняет в базу.
    :param session: AsyncSession SQLAlchemy
    :param country_id: id страны в локной базе
    :param country_name: имя страны в локной базе
    :param api_country_code: код ISO страны (пример: "US")
    :param api_country_id: id страны в API
    """

    has_next_page = True
    after_cursor = None
    page = 1

    async with httpx.AsyncClient(timeout=30) as client:
        while has_next_page:
            params = {
                "type": "city",
                "countryCode": api_country_code,
                "first": 100,
                "countryId": api_country_id,
            }
            if after_cursor:
                params["after"] = after_cursor

            try:
                response = await client.get(API_URL, headers=HEADERS, params=params)
            except Exception as e:
                print(f"Ошибка запроса к API для страны id={country_id}: {e}")
                break

            if response.status_code != 200:
                print(f"API error for country id={country_id}: {response.status_code} - {response.text}")
                break

            data = response.json()
            edges = data.get("edges", [])
            page_info = data.get("pageInfo", {})

            new_cities_count = 0
            n = 0
            # print(f"{edges=}")
            for edge in edges:
                node = edge.get("node")
                if not node:
                    continue
                city_name = node.get("name")
                latitude = node.get("latitude")
                longitude = node.get("longitude")
                population = node.get("population", 0)
                description = node.get("id")
                print(f"№ {n}, {node.get('id')=} город {city_name},")
                n += 1
                if not all([city_name, latitude, longitude]):
                    continue

                dto_create = CityCreateDTO(
                    country_id=country_id,
                    name=city_name,
                    name_eng=city_name,  # можно поменять при необходимости
                    latitude=latitude,
                    longitude=longitude,
                    population=int(population or 0),
                    description=description,
                )

                try:
                    await CityModel.create(session, dto_create)
                    new_cities_count += 1
                except IntegrityError:
                    await session.rollback()
                except Exception as e:
                    await session.rollback()
                    print(f"Ошибка при сохранении города {city_name}: {e}")

            print(f"Страница {page}: добавлено {new_cities_count} городов для страны {country_name} (id={country_id})")

            has_next_page = page_info.get("hasNextPage", False)
            after_cursor = page_info.get("endCursor")
            page += 1

            await asyncio.sleep(randint(1, 3))  # имитация паузы


COUNTRIES_FILE = Path("countries_for_cities.json")


async def save_countries_to_json(session: AsyncSession):
    """
    Получает список стран из базы и сохраняет в JSON.
    """
    query = select(CountryModel.id, CountryModel.name, CountryModel.iso_code, CountryModel.description)
    result = await session.execute(query)
    countries = [
        {"id": row.id, "name": row.name, "iso_code": row.iso_code, "api_country_id": row.description}
        for row in result.all()
    ]

    COUNTRIES_FILE.write_text(json.dumps(countries, ensure_ascii=False, indent=4))
    print(f"Сохранено {len(countries)} стран в {COUNTRIES_FILE}")


async def run():
    async with AsyncSessionLocal() as session:
        # 1. Сохраняем список стран в JSON
        # await save_countries_to_json(session)

        # 2. Читаем страны из JSON
        countries = json.loads(COUNTRIES_FILE.read_text())

        # 3. Парсим города по каждой стране
        for country in countries:
            if country["id"] >= 220:  # временное решение
                # continue
                await fetch_and_save_cities(
                    session,
                    country_id=country["id"],
                    country_name=country["name"],
                    api_country_code=country["iso_code"],
                    api_country_id=country["api_country_id"],
                )


if __name__ == "__main__":
    asyncio.run(run())
