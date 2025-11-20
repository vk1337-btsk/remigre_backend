import logging
from typing import Optional, Union

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.db_config import get_async_session
from src.ms_metric.schemas.schemas import MetricDetailSchema, MetricOnlyListSchema
from src.ms_metric.services.db_metric_service import DB_MetricService


class MetricService:

    def __init__(self, session: AsyncSession = Depends(get_async_session)):
        """Инициализация основных параметров."""

        self.service_db = DB_MetricService(session)

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
        country_id: Optional[int] = None,
        country_name: Optional[str] = None,
        only_list: Optional[bool] = True,
    ):

        if country_id:
            result = await self.service_db.get_all_metrics_country_by_id(country_id)
            return result
        elif country_name:
            result = await self.service_db.get_all_metrics_country_by_name(country_name)
            return result
