from typing import Union

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.db_config import get_async_session
from src.ms_location.schemas.schemas import CountryOnlyListSchema
from src.ms_location.services.db_location_service import DB_LocationService


class LocationService:

    def __init__(self, session: AsyncSession = Depends(get_async_session)):
        """Инициализация основных параметров."""

        self.service_db = DB_LocationService(session)

    async def search_location_by_part_word(self, part_word: str):

        result = await self.service_db.get_locations_by_part_name(part_word)

    async def get_countries(self, only_list: bool) -> Union[list[CountryOnlyListSchema], None]:

        if only_list:
            result = await self.service_db.get_all_countries_only_list()
            return result
        else:
            pass


"""
# TODO:
1. Сделать эндпоинты лист стран и городов
2. Сделать эндпоинт детальной инфы по городу
3. Список метрик
"""
