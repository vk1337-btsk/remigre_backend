import logging
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple, cast

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.dependency import get_async_session, get_sessionmaker
from src.ms_location.schemas import (
    Body_GetCLocationByCoordinates,
    ListPaginatedCountryShortInfo,
    LocationMainInfoSchema,
    MetricInfoSchema,
    MetricValueSchema,
    ShortMetricInfoDTO,
)
from src.ms_location.services.db_service import DB_LocationService
from src.ms_location.services.handlers import metric_handlers


logger = logging.getLogger(__name__)

AttributeHandler = Callable[[Dict[str, List[str]]], Dict[str, str]]  # Тип функции помощника


class LocationService:

    def __init__(
        self,
        session: AsyncSession = Depends(get_async_session),
        session_factory: async_sessionmaker[AsyncSession] = Depends(get_sessionmaker),
    ):
        """Инициализация основных параметров."""

        self._async_session = session
        self._session_factory = session_factory
        self.service_db = DB_LocationService(session, session_factory)

        self._metric_handlers: Dict[int, AttributeHandler] = {}

        self._type_map = None
        self._value_map = None
        self._cache_time = None

        self._metric_handlers = metric_handlers

    def register_metric_handler(self, metric_id: int, handler: AttributeHandler):
        self._metric_handlers[metric_id] = handler

    async def _get_attribute_mappings_cached(self):
        # Проверяем время кэша (например, 5 минут)

        if not self._cache_time or (datetime.now() - self._cache_time).seconds > 300:
            self._type_map, self._value_map = await self.service_db._get_attribute_mappings()
            self._cache_time = datetime.now()
        return self._type_map, self._value_map

    #
    #
    # ============ Общие методы для работы c локациями ============
    async def search_location_by_part_word(self, part_word: str) -> list[LocationMainInfoSchema]:
        """Осуществляет поиск стран/городов по их названию и возвращает список из вариантов."""

        return await self.service_db.get_locations_by_part_word(part_word)

    async def get_coordinates_locations_for_map(self, tolerance: Optional[float] = 0.1) -> dict:
        """Возвращает координаты и границы активных стран для карты"""

        tolerance = 0.1 if tolerance is None else tolerance
        return await self.service_db.get_coordinates_locations_for_map(tolerance)

    async def get_location_by_coordinates_from_map(
        self, body: Body_GetCLocationByCoordinates
    ) -> LocationMainInfoSchema:
        """Возвращает основную информацию об объекте локации по его координатам."""

        row = await self.service_db.get_location_by_coordinates_from_map(
            location_type=body.type, latitude=body.latitude, longitude=body.longitude
        )

        return LocationMainInfoSchema(id=row["id"], type=body.type, name=row["name"], iso_code=row["iso_code"])

    #
    #
    # ============ Работа со странами ============
    async def get_list_countries(self, page: int, size: int) -> ListPaginatedCountryShortInfo:
        """Возвращает список стран с основными метриками"""

        # Получаю общее кол-во активных стран и список активных стран с характеристиками для текущей страницы
        total, countries = await self.service_db.get_active_countries_for_short_list(page=page, size=size)

        # Если нет стран
        if not countries:
            return ListPaginatedCountryShortInfo(total=total, items=[])

        countries_ids = [country.id for country in countries]

        # Получаю сырые данные метрик по пресетам
        raw_metrics = await self.service_db.get_metrics_for_short_list_countries(countries_ids)

        # Получаю наименования типов и значений атрибутов
        type_map, value_map = await self._get_attribute_mappings_cached()
        type_map = cast(Dict[str, str], type_map)
        value_map = cast(Dict[Tuple, str], value_map)

        # Редактирую метрики
        enriched_metrics = self._edit_metrics(raw_metrics, type_map, value_map)

        for country in countries:
            country.metrics = enriched_metrics.get(country.id, [])

        return ListPaginatedCountryShortInfo(total=total, items=countries)

    #
    #
    # ============ Вспомогательные методы ============
    def _edit_metrics(
        self,
        raw_metrics_by_country: Dict[int, List[ShortMetricInfoDTO]],
        type_map: Dict[str, str],
        value_map: Dict[tuple, str],
    ) -> Dict[int, List[MetricInfoSchema]]:
        """Преобразует сырые метрики (с кодами атрибутов) в финальные схемы с названиями типов и значений."""

        result = {}
        for country_id, metrics in raw_metrics_by_country.items():
            enriched_metrics = []
            for metric in metrics:
                enriched_values = []

                # Получаем обработчик для текущей метрики (если есть)
                handler = self._metric_handlers.get(metric.id)

                for val in metric.values:

                    # Преобразуем атрибуты: ключи становятся названиями типов, значения — списками названий
                    enriched_attrs = {}
                    for type_code, value_codes in val.attributes.items():
                        type_name = type_map.get(type_code, type_code)  # получаем название типа (fallback на код)
                        # получаем названия для каждого значения
                        value_names = [value_map.get((type_code, vc), vc) for vc in value_codes]
                        enriched_attrs[type_name] = value_names

                    # Применяем кастомный обработчик, если зарегистрирован
                    if handler:
                        enriched_attrs = handler(enriched_attrs)

                    # Формируем единое значение value в зависимости от типа
                    if val.value_numeric is not None:
                        value = val.value_numeric
                    elif val.value_string is not None:
                        value = val.value_string
                    elif val.value_boolean is not None:
                        value = val.value_boolean
                    elif val.value_range_start is not None and val.value_range_end is not None:
                        value = [val.value_range_start, val.value_range_end]
                    else:
                        value = None

                    enriched_values.append(
                        MetricValueSchema(
                            value=value, year=val.year, attributes=enriched_attrs, priority=metric.display_priority
                        )
                    )

                enriched_metrics.append(
                    MetricInfoSchema(id=metric.id, name=metric.name, type=metric.type, values=enriched_values)
                )
            result[country_id] = enriched_metrics
        return result
