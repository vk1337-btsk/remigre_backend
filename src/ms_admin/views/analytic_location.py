from fastapi import Request, Response
from sqlalchemy import text
from starlette_admin import CustomView


class LocationAnalyticsView(CustomView):
    """Аналитика по странам и городам: страны без активных городов и города в неактивных странах"""

    label = "Аналитика стран/городов"
    icon = "fa fa-globe"

    async def render(self, request: Request, templates) -> Response:
        session = request.state.session

        # 1. Страны, которые активны, но не имеют ни одного активного города
        countries_without_cities = []
        sql_countries = text(
            """
            SELECT c.id, c.name, c.is_active
            FROM loc_country c
            WHERE c.is_active = true
              AND NOT EXISTS (
                SELECT 1 FROM loc_city city
                WHERE city.country_id = c.id
                  AND city.is_active = true
              )
            ORDER BY c.name
        """
        )
        result = await session.execute(sql_countries)
        countries_without_cities = result.fetchall()

        # 2. Города, которые активны, но их страна неактивна
        cities_with_inactive_country = []
        sql_cities = text(
            """
            SELECT city.id, city.name, city.is_active AS city_active,
                   c.id AS country_id, c.name AS country_name, c.is_active AS country_active
            FROM loc_city city
            JOIN loc_country c ON city.country_id = c.id
            WHERE city.is_active = true
              AND c.is_active = false
            ORDER BY city.name
        """
        )
        result = await session.execute(sql_cities)
        cities_with_inactive_country = result.fetchall()

        # 3. Общая статистика (необязательно)
        stats = {
            "total_countries": 0,
            "total_cities": 0,
            "active_countries": 0,
            "active_cities": 0,
            "countries_without_cities": len(countries_without_cities),
            "cities_with_inactive_country": len(cities_with_inactive_country),
        }

        stats_sql = text(
            """
            SELECT
                (SELECT COUNT(*) FROM loc_country) AS total_countries,
                (SELECT COUNT(*) FROM loc_city) AS total_cities,
                (SELECT COUNT(*) FROM loc_country WHERE is_active = true) AS active_countries,
                (SELECT COUNT(*) FROM loc_city WHERE is_active = true) AS active_cities
        """
        )
        stats_result = await session.execute(stats_sql)
        stats_row = stats_result.fetchone()
        if stats_row:
            stats.update(
                {
                    "total_countries": stats_row.total_countries,
                    "total_cities": stats_row.total_cities,
                    "active_countries": stats_row.active_countries,
                    "active_cities": stats_row.active_cities,
                }
            )

        return templates.TemplateResponse(
            "location_analytics.html",
            {
                "request": request,
                "countries_without_cities": countries_without_cities,
                "cities_with_inactive_country": cities_with_inactive_country,
                "stats": stats,
            },
        )
