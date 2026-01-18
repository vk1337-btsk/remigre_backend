import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.database import GetFilteredListDTO
from src.ms_location.models import CountryModel
from src.ms_metric.dto import MetricInfoGetDTO, MetricInfoOptionsDTO
from src.ms_metric.models import (
    MetricDataModel,
    MetricInfoModel,
    MetricPeriodModel,
    MetricSeriesModel,
)
from src.ms_metric.schemas import MetricDetailSchema


logger = logging.getLogger(__name__)


class DB_MetricService:

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        """Инициализация основных параметров."""

        self._session_factory = session_factory

    async def get_all_metrics(self) -> list[MetricDetailSchema]:

        async with self._session_factory() as session:
            result = await MetricInfoModel.get_all_filtered(
                session, dto_filters=GetFilteredListDTO(filters={"is_active": True})
            )
            return [MetricDetailSchema.model_validate(metric) for metric in result]

    async def get_metric(self, slug: str) -> MetricDetailSchema:

        async with self._session_factory() as session:
            result = await MetricInfoModel.get(session, dto_get=MetricInfoGetDTO(slug=slug))
            return MetricDetailSchema.model_validate(result)

    async def get_all_metrics_country_by_id(self, country_id: int):
        """Получить все метрики по стране с использованием DTO и классовых методов MetricModel."""

        async with self._session_factory() as session:
            stmt = (
                select(
                    MetricInfoModel,
                    MetricSeriesModel.add_info,
                )
                .join(MetricSeriesModel, MetricSeriesModel.metric_id == MetricInfoModel.id)
                .join(MetricDataModel, MetricDataModel.series_id == MetricSeriesModel.id)
                .where(MetricDataModel.country_id == country_id)
                .where(
                    MetricInfoModel.is_active.is_(True),
                    MetricSeriesModel.is_active.is_(True),
                )
            )

            result = await session.execute(stmt)
            rows = result.all()

            return self._serialize_metrics(rows)

    def _serialize_metrics(self, rows):
        metrics: dict[int, dict] = {}

        for metric, add_info in rows:
            metric_id = metric.id

            if metric_id not in metrics:
                metrics[metric_id] = {
                    "metric_id": metric.id,
                    "slug": metric.slug,
                    "name": metric.name,
                    "category": metric.category,
                    "description": metric.description,
                    "filters": {},
                }

            # add_info может быть None
            if not add_info:
                continue

            for key, value in add_info.items():
                filters = metrics[metric_id]["filters"]

                if key not in filters:
                    filters[key] = set()

                # если значение массив — разворачиваем
                if isinstance(value, list):
                    filters[key].update(value)
                else:
                    filters[key].add(value)

        # set → list (для JSON)
        for metric in metrics.values():
            metric["filters"] = {key: sorted(values) for key, values in metric["filters"].items()}

        return list(metrics.values())

    #
    #
    # ===================== Операции, связывающие метрики и страны =====================
    # async def
