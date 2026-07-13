import logging

from sqlalchemy import text
from starlette.requests import Request
from starlette.responses import Response
from starlette_admin import CustomView

logger = logging.getLogger(__name__)


class MetricAnalyticsView(CustomView):
    """Админка для аналитики метрик"""

    label = "Аналитика метрик"
    icon = "fa fa-chart-line"

    async def render(self, request: Request, templates) -> Response:
        """Рендер кастомной страницы для аналитики метрики"""

        session = request.state.session
        # Получаем список метрик
        metrics_result = await session.execute(text("SELECT id, name, slug FROM metric_info ORDER BY name"))
        metrics = metrics_result.fetchall()

        metric_id = request.query_params.get("metric_id")
        data = []
        total_series = None
        series_with_attributes = None
        total_attr_types = None
        total_attr_combinations = None

        if metric_id:
            try:
                metric_id = int(metric_id)
            except ValueError:
                metric_id = None

            if metric_id:
                # Один запрос для получения всех агрегатных показателей
                agg_sql = text(
                    """
                    WITH target_series AS (
                        SELECT id AS series_id
                        FROM metric_series
                        WHERE metric_id = :metric_id AND is_active = true
                    )
                    SELECT
                        (SELECT COUNT(*) FROM target_series) AS total_series,
                        (SELECT COUNT(DISTINCT series_id) FROM metric_series_attribute
                         WHERE series_id IN (SELECT series_id FROM target_series)) AS series_with_attributes,
                        (SELECT COUNT(DISTINCT at.id)
                         FROM metric_series_attribute msa
                         JOIN metric_attribute_type at ON msa.attribute_type_id = at.id AND at.is_active = true
                         WHERE msa.series_id IN (SELECT series_id FROM target_series)) AS total_attr_types,
                        (SELECT COUNT(DISTINCT (at.id, av.id))
                         FROM metric_series_attribute msa
                         JOIN metric_attribute_type at ON msa.attribute_type_id = at.id AND at.is_active = true
                         JOIN metric_attribute_value av ON msa.attribute_value_id = av.id AND av.is_active = true
                         WHERE msa.series_id IN (SELECT series_id FROM target_series)) AS total_attr_combinations
                    """
                )
                agg_result = await session.execute(agg_sql, {"metric_id": metric_id})
                agg_row = agg_result.fetchone()
                total_series = agg_row.total_series if agg_row else 0
                series_with_attributes = agg_row.series_with_attributes if agg_row else 0
                total_attr_types = agg_row.total_attr_types if agg_row else 0
                total_attr_combinations = agg_row.total_attr_combinations if agg_row else 0

                # Если есть серии с атрибутами, выполняем детальный запрос
                if series_with_attributes > 0:
                    detail_sql = text(
                        """
                        WITH target_series AS (
                            SELECT id AS series_id
                            FROM metric_series
                            WHERE metric_id = :metric_id AND is_active = true
                        ),
                        type_series_counts AS (
                            SELECT
                                at.id AS type_id,
                                COUNT(DISTINCT ts.series_id) AS total_series_for_type
                            FROM target_series ts
                            JOIN metric_series_attribute msa ON ts.series_id = msa.series_id
                            JOIN metric_attribute_type at ON msa.attribute_type_id = at.id AND at.is_active = true
                            GROUP BY at.id
                        )
                        SELECT
                            at.code AS type_code,
                            at.name AS type_name,
                            av.code AS value_code,
                            av.name AS value_name,
                            COUNT(DISTINCT ts.series_id) AS series_count,
                            tsc.total_series_for_type
                        FROM target_series ts
                        JOIN metric_series_attribute msa ON ts.series_id = msa.series_id
                        JOIN metric_attribute_type at ON msa.attribute_type_id = at.id AND at.is_active = true
                        JOIN metric_attribute_value av ON msa.attribute_value_id = av.id AND av.is_active = true
                        LEFT JOIN type_series_counts tsc ON at.id = tsc.type_id
                        GROUP BY at.code, at.name, av.code, av.name, tsc.total_series_for_type
                        HAVING COUNT(DISTINCT ts.series_id) > 1
                        ORDER BY series_count DESC;
                        """
                    )
                    result = await session.execute(detail_sql, {"metric_id": metric_id})
                    data = result.fetchall()

        series_without_attributes = total_series - series_with_attributes if total_series is not None else None
        percent_with_attrs = (
            (series_with_attributes / total_series * 100) if total_series and series_with_attributes else 0
        )

        return templates.TemplateResponse(
            "metric_analytics.html",
            {
                "request": request,
                "metrics": metrics,
                "selected_metric_id": metric_id,
                "data": data,
                "total_series": total_series,
                "series_with_attributes": series_with_attributes,
                "series_without_attributes": series_without_attributes,
                "percent_with_attrs": percent_with_attrs,
                "total_attr_types": total_attr_types,
                "total_attr_combinations": total_attr_combinations,
            },
        )
