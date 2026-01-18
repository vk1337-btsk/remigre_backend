import logging
from typing import Optional, Union

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.database.database import get_async_session_factory
from src.ms_metric.schemas.schemas import MetricDetailSchema, MetricOnlyListSchema
from src.ms_metric.services.db_metric_service import DB_MetricService


class MetricService:

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] = Depends(get_async_session_factory)):
        """Инициализация основных параметров."""

        self.service_db = DB_MetricService(session_factory)

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

    async def get_metric(self, slug: str) -> MetricDetailSchema:
        """Возвращает метрику с детальной информацией."""

        result = await self.service_db.get_metric(slug)
        return result

    async def get_all_metrics_for_country(
        self,
        country_id: int,
        only_list: Optional[bool] = True,
    ):
        result = await self.service_db.get_all_metrics_country_by_id(country_id)
        return result
