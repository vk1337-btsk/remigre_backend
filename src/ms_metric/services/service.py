import logging
from typing import Optional, Union

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.dependency import get_async_session, get_sessionmaker
from src.ms_metric.schemas import (
    Body_GetLocationsByFilters,
    MetricDetailSchema,
    MetricOnlyListSchema,
)
from src.ms_metric.services.db_service import DB_MetricService


class MetricService:

    def __init__(
        self,
        session: AsyncSession = Depends(get_async_session),
        session_factory: async_sessionmaker[AsyncSession] = Depends(get_sessionmaker),
    ):
        """Инициализация основных параметров."""

        self._async_session = session
        self.service_db = DB_MetricService(session, session_factory)

    #
    #
    # ============ Общие методы ============
    # async def get_filters_info(self):

    #     return FiltersInfo(
    #         category=[e.value for e in CategoryMetricEnum],
    #         gender=[e.value for e in FiltredMetricGenderEnum],
    #     )

    async def get_county_and_city_by_filter(self, body: Body_GetLocationsByFilters):
        """Возвращает список стран и городов по полученным фильтрам"""

        pass

    #
    #
    # ============ Работа c локациями ============
    async def get_all_metrics(
        self,
        only_list: bool,
    ) -> Union[list[MetricOnlyListSchema], list[MetricDetailSchema]]:
        """Возвращает список всех метрик с основной или детальной информацией в зависимости от query параметра."""

        if only_list:
            result = [MetricOnlyListSchema.model_validate(el) for el in await self.service_db.get_all_metrics()]
            return result
        else:
            result = await self.service_db.get_all_metrics()
            return result

    async def get_metric(self, id: int) -> MetricDetailSchema:
        """Возвращает метрику с детальной информацией."""

        result = await self.service_db.get_metric(id)
        return result

    async def get_all_metrics_for_country(
        self,
        country_id: int,
    ):
        result = await self.service_db.get_all_metrics_country_by_id(country_id)
        return result

    async def get_all_metrics_for_city(
        self,
        city_id: int,
    ):
        result = await self.service_db.get_all_metrics_city_by_id(city_id)
        return result
