import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import GetFilteredListDTO
from src.ms_location.models import CountryModel
from src.ms_metric.dto import MetricGetDTO, MetricOptionsDTO
from src.ms_metric.models import MetricDataModel, MetricModel, MetricPeriodModel
from src.ms_metric.schemas import MetricDetailSchema


logger = logging.getLogger(__name__)


class DB_MetricService:

    def __init__(self, async_session: AsyncSession):
        """Инициализация основных параметров."""

        self._async_session = async_session

    async def get_all_metrics(self) -> list[MetricDetailSchema]:

        result = await MetricModel.get_all_filtered(
            self._async_session, dto_filters=GetFilteredListDTO(filters={"is_active": True})
        )
        return [MetricDetailSchema.model_validate(metric) for metric in result]

    async def get_metric(self, slug: str) -> MetricDetailSchema:
        result = await MetricModel.get(self._async_session, dto_get=MetricGetDTO(slug=slug))
        return MetricDetailSchema.model_validate(result)

    async def get_all_metrics_country_by_id(self, country_id: int):
        """
        Получить все метрики по стране с использованием DTO и классовых методов MetricModel.
        """

        # Сначала находим все metric_id для страны
        stmt = select(MetricDataModel.metric_id).where(MetricDataModel.country_id == country_id).distinct()
        result = await self._async_session.execute(stmt)
        metric_ids = [row[0] for row in result.fetchall()]

        if not metric_ids:
            return []

        # Теперь достаём метрики через MetricModel.get_all_filtered
        dto_options = MetricOptionsDTO(with_period=True, with_data=True)
        metrics = await MetricModel.get_all_filtered(
            session=self._async_session,
            dto_filters=None,  # можно будет добавить фильтры если понадобится
            dto_options=dto_options,
            related_filters={"data": {"country_id": country_id}},
        )

        return metrics

    async def get_all_metrics_country_by_name(self, country_name: str):
        """
        Получить все метрики по стране с использованием DTO и классовых методов MetricModel.
        """

        # Находим ID страны по name_eng
        stmt_country = select(CountryModel.id).where(CountryModel.name_eng == country_name)
        result_country = await self._async_session.execute(stmt_country)
        country_id = result_country.scalar_one_or_none()

        if not country_id:
            return []

        # Достаём все уникальные metric_id для этой страны
        stmt_metrics = select(MetricDataModel.metric_id).where(MetricDataModel.country_id == country_id).distinct()
        result_metrics = await self._async_session.execute(stmt_metrics)
        metric_ids = [row[0] for row in result_metrics.fetchall()]

        if not metric_ids:
            return []

        # Подгружаем сами метрики через MetricModel с DTO
        dto_options = MetricOptionsDTO(with_period=True, with_data=True)
        metrics = await MetricModel.get_all_filtered(
            session=self._async_session,
            dto_filters=None,
            dto_options=dto_options,
            related_filters={"data": {"country_id": country_id}},
        )

        return metrics
