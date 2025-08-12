import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.ms_location.dto.country_dto import CountryOptionsDTO
from src.ms_location.models import CityModel, CountryModel, RegionModel
from src.ms_location.schemas.schemas import CountryOnlyListSchema


logger = logging.getLogger(__name__)


class DB_LocationService:

    def __init__(self, async_session: AsyncSession):
        """Инициализация основных параметров."""

        self._async_session = async_session

    async def get_locations_by_part_name(self, part_name: str):

        result_country = await CountryModel.get_all_filtered(self._async_session)

    async def get_all_countries_only_list(self) -> list[CountryOnlyListSchema]:

        result = await CountryModel.get_all_filtered(
            self._async_session, dto_options=CountryOptionsDTO(with_region=False, with_city=False, with_data=False)
        )
        return [CountryOnlyListSchema.model_validate(country) for country in result]
