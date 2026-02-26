import json
import logging
from typing import Dict, List, Literal, Tuple

from fastapi import HTTPException
from sqlalchemy import and_, func, literal, select, text, true, union_all
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.m_views.mv_short_latest import MV_LocationShortLatestMetrics
from src.core.models import (
    CityModel,
    CountryModel,
    MetricAttributeTypeModel,
    MetricAttributeValueModel,
    MetricInfoModel,
    MetricPresetModel,
)
from src.ms_location.schemas import (
    CityDetailSchema,
    CountryDetailSchema,
    CountryShortInfoDetail,
    LocationMainInfoSchema,
)
from src.ms_location.schemas.schemas import (
    ListPaginatedCountryShortInfo,
    MetricInfoSchema,
    MetricValueSchema,
    ShortMetricInfoDTO,
    ShortMetricValueDTO,
)


logger = logging.getLogger(__name__)


class DB_LocationService:

    def __init__(self, session: AsyncSession, session_factory: async_sessionmaker[AsyncSession]):
        """Инициализация основных параметров."""

        self._async_session = session
        self._session_factory = session_factory

    #
    #
    # ============ Операции с локациями ============
    async def get_locations_by_part_word(self, part_word: str) -> list[LocationMainInfoSchema]:
        """Осуществляет поиск стран и городов по части их названия"""

        search = f"%{part_word}%"

        # Запрос для стран
        country_stmt = select(
            CountryModel.id.label("id"),
            literal("country").label("type"),
            CountryModel.name.label("name"),
            CountryModel.iso_alpha_2.label("iso_code"),
        ).where(
            CountryModel.is_active.is_(True),
            CountryModel.name.ilike(search),
        )

        # Запрос для городов
        city_stmt = (
            select(
                CityModel.id.label("id"),
                literal("city").label("type"),
                CityModel.name.label("name"),
                CountryModel.iso_alpha_2.label("iso_code"),
            )
            .join(CountryModel, CityModel.country_id == CountryModel.id)
            .where(
                CityModel.is_active.is_(True),
                CityModel.name.ilike(search),
            )
        )

        stmt = union_all(country_stmt, city_stmt)  # Объединяем запросы
        result = await self._async_session.execute(stmt)  # Получаем результат

        return [LocationMainInfoSchema.model_validate(obj) for obj in result.mappings().all()]

    async def get_coordinates_locations_for_map(self, tolerance: float) -> dict:
        """Возвращает координаты и границы активных стран для карты"""

        sql = text(
            """
            SELECT jsonb_build_object(
                'countries', jsonb_build_object(
                    'type', 'FeatureCollection',
                    'features', countries.features
                ),
                'cities', jsonb_build_object(
                    'type', 'FeatureCollection',
                    'features', cities.features
                )
            ) AS geojson
            FROM
            (
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'type', 'Feature',
                        'geometry', ST_AsGeoJSON(
                            COALESCE(
                                ST_SimplifyPreserveTopology(c.geometry, :tolerance),
                                c.geometry
                            )
                        )::jsonb,
                        'properties', jsonb_build_object(
                            'id', c.id,
                            'name', c.name
                        )
                    )
                ) AS features
                FROM loc_country c
                WHERE c.is_active = TRUE
                AND c.geometry IS NOT NULL
                AND ST_IsValid(c.geometry)
            ) countries,
            (
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'type', 'Feature',
                        'geometry', ST_AsGeoJSON(
                            ST_SetSRID(ST_MakePoint(ci.longitude, ci.latitude), 4326)
                        )::jsonb,
                        'properties', jsonb_build_object(
                            'id', ci.id,
                            'name', ci.name,
                            'is_capital', ci.is_capital
                        )
                    )
                ) AS features
                FROM loc_city ci
                WHERE ci.is_active = TRUE
            ) cities;
            """
        )
        result = await self._async_session.execute(sql, {"tolerance": tolerance})
        return result.scalar_one()

    async def get_location_by_coordinates_from_map(
        self, location_type: Literal["city", "country"], latitude: float, longitude: float
    ):
        """Осуществляет поиск страны или города по его координатам."""

        point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)

        if location_type == "city":
            stmt = (
                select(
                    CityModel.id.label("id"),
                    CityModel.name.label("name"),
                    CountryModel.iso_alpha_2.label("iso_code"),
                )
                .join(CountryModel, CityModel.country_id == CountryModel.id)
                .where(
                    and_(
                        CityModel.latitude == latitude,
                        CityModel.longitude == longitude,
                        CityModel.is_active.is_(True),
                    )
                )
                .limit(1)
            )

        else:  # country
            stmt = (
                select(
                    CountryModel.id.label("id"),
                    CountryModel.name.label("name"),
                    CountryModel.iso_alpha_2.label("iso_code"),
                )
                .where(
                    and_(
                        CountryModel.is_active.is_(True),
                        func.ST_Contains(CountryModel.geometry, point),
                    )
                )
                .limit(1)
            )

        result = await self._async_session.execute(stmt)
        row = result.mappings().first()

        if not row:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"{'Город' if location_type == 'city' else 'Страна'} "
                    f"по координатам ({latitude}, {longitude}) не найден(а)."
                ),
            )

        return row

    #
    #
    # ============ Работа со странами ============
    async def get_active_countries_for_short_list(
        self, limit: int, offset: int
    ) -> Tuple[int, List[CountryShortInfoDetail]]:
        """Возвращает список активных стран с поддер"""

        stmt = (
            select(
                CountryModel.id,
                CountryModel.name,
                CountryModel.iso_alpha_2,
                CountryModel.population,
                func.count().over().label("total"),
            )
            .where(CountryModel.is_active == True)
            .order_by(CountryModel.name)
            .limit(limit)
            .offset(offset)
        )
        result = await self._async_session.execute(stmt)
        rows = result.all()

        if not rows:
            return 0, []

        total = rows[0].total
        items = [
            CountryShortInfoDetail(id=row.id, name=row.name, iso_alpha_2=row.iso_alpha_2, population=row.population)
            for row in rows
        ]
        return total, items

    async def get_metrics_for_short_list_countries(self, country_ids: List[int]) -> Dict[int, List[ShortMetricInfoDTO]]:
        """

        Возвращает словарь, где ключ — ID страны, значение — список метрик c данными о них ().
        Учитываются только пресеты, помеченные for_country_list = True.
        """

        if not country_ids:
            return {}

        data_stmt = (
            select(
                MV_LocationShortLatestMetrics.country_id,
                MV_LocationShortLatestMetrics.metric_id,
                MV_LocationShortLatestMetrics.period_year,
                MV_LocationShortLatestMetrics.value_numeric,
                MV_LocationShortLatestMetrics.value_string,
                MV_LocationShortLatestMetrics.value_boolean,
                MV_LocationShortLatestMetrics.value_range_start,
                MV_LocationShortLatestMetrics.value_range_end,
                MV_LocationShortLatestMetrics.attributes,
                MetricInfoModel.name,
                MetricInfoModel.data_type,
                MetricInfoModel.data_type,
                MetricPresetModel.display_priority,
            )
            .join(
                MetricInfoModel,
                (MetricInfoModel.id == MV_LocationShortLatestMetrics.metric_id) & (MetricInfoModel.is_active == True),
            )
            .join(
                MetricPresetModel,
                MetricPresetModel.id == MV_LocationShortLatestMetrics.preset_id,
            )
            .where(MV_LocationShortLatestMetrics.country_id.in_(country_ids))
            .where(MetricPresetModel.for_country_list == True, MetricPresetModel.is_active == True)
            .order_by(MV_LocationShortLatestMetrics.country_id, MV_LocationShortLatestMetrics.metric_id)
        )
        data_result = await self._async_session.execute(data_stmt)
        rows = data_result.all()

        result_dict = {}
        for row in rows:
            cid = row.country_id
            mid = row.metric_id
            priority = row.display_priority

            if cid not in result_dict:
                result_dict[cid] = {}

            if mid not in result_dict[cid]:
                # Создаём запись метрики с текущим приоритетом
                result_dict[cid][mid] = ShortMetricInfoDTO(
                    id=mid,
                    name=row.name,
                    type=row.data_type,
                    values=[],
                    display_priority=priority,
                )
                result_dict[cid][mid].display_priority = priority

            # Добавляем значение
            value_dto = ShortMetricValueDTO(
                value_numeric=row.value_numeric,
                value_string=row.value_string,
                value_boolean=row.value_boolean,
                value_range_start=row.value_range_start,
                value_range_end=row.value_range_end,
                year=row.period_year,
                attributes=row.attributes or {},
            )
            result_dict[cid][mid].values.append(value_dto)

        # Формируем финальный ответ для всех запрошенных стран
        final_result = {}
        for cid in country_ids:
            if cid in result_dict:
                metrics_list = list(result_dict[cid].values())
                # Сортируем метрики: сначала по display_priority (меньше = выше), затем по имени
                metrics_list.sort(key=lambda m: (m.display_priority or 0, m.name))
                final_result[cid] = metrics_list
            else:
                final_result[cid] = []
        return final_result

    async def _get_attribute_mappings(self) -> Tuple[Dict[str, str], Dict[tuple, str]]:
        """
        Возвращает:
        - type_map: dict {type_code: type_name}
        - value_map: dict {(type_code, value_code): value_name}
        """

        # Загружаем активные типы
        type_stmt = select(MetricAttributeTypeModel.code, MetricAttributeTypeModel.name).where(
            MetricAttributeTypeModel.is_active == True
        )
        type_result = await self._async_session.execute(type_stmt)
        type_map = {row.code: row.name for row in type_result.all()}

        # Загружаем активные значения с их типами
        value_stmt = (
            select(
                MetricAttributeValueModel.code,
                MetricAttributeValueModel.name,
                MetricAttributeTypeModel.code.label("type_code"),
            )
            .join(MetricAttributeTypeModel, MetricAttributeValueModel.attribute_type_id == MetricAttributeTypeModel.id)
            .where(MetricAttributeValueModel.is_active == True, MetricAttributeTypeModel.is_active == True)
        )

        value_result = await self._async_session.execute(value_stmt)
        value_map = {}

        for row in value_result.all():
            key = (row.type_code, row.code)
            value_map[key] = row.name

        return type_map, value_map
