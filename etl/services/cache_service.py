# etl/services/cache_service.py
"""
Асинхронный сервис для управления всеми кэшами ETL
"""

import time
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from etl.config.etl_config import ETLConfig
from etl.utils.lru_caches import AsyncLRUCache
from src.core.config.logging import setup_logger_to_file
from src.core.models import (
    CountryModel,
    MetricAttributeTypeModel,
    MetricAttributeValueModel,
    MetricInfoModel,
    MetricPeriodModel,
    MetricSeriesAttribute,
    MetricSeriesModel,
)


logger = setup_logger_to_file()


class CacheService:
    """Управление всеми кэшами ETL. Все операции get/set асинхронны."""

    def __init__(self, config: ETLConfig):
        """Инициализация параметров"""

        self.config = config

        self._country_cache = AsyncLRUCache(maxsize=self.config.cache.country_size, name=self.config.cache.country_name)
        self._city_cache = AsyncLRUCache(maxsize=self.config.cache.city_size, name=self.config.cache.city_name)
        self._metric_cache = AsyncLRUCache(maxsize=self.config.cache.metric_size, name=self.config.cache.metric_name)
        self._series_cache = AsyncLRUCache(maxsize=self.config.cache.series_size, name=self.config.cache.series_name)
        self._period_cache = AsyncLRUCache(maxsize=self.config.cache.period_size, name=self.config.cache.period_name)
        self._attr_type_cache = AsyncLRUCache(
            maxsize=self.config.cache.attr_type_size, name=self.config.cache.attr_type_name
        )
        self._attr_value_cache = AsyncLRUCache(
            maxsize=self.config.cache.attr_value_size, name=self.config.cache.attr_value_name
        )
        self._caches = {
            "country": self._country_cache,
            "city": self._city_cache,
            "metric": self._metric_cache,
            "series": self._series_cache,
            "period": self._period_cache,
            "attribute_type": self._attr_type_cache,
            "attribute_value": self._attr_value_cache,
        }

        self._countries_preloaded = False

    #
    #
    #
    # ================= Статистика и очистка =================
    def get_cache_stats(self) -> Dict[str, dict]:
        """Возвращает статистику по кэшированию"""

        return {name: cache.stats() for name, cache in self._caches.items()}

    async def clear_all(self) -> None:
        """Очищает все кэши"""

        for cache in self._caches.values():
            await cache.clear()

        self._countries_preloaded = False
        logger.info("✅ Все кэши очищены")

    #
    #
    #
    # ================= Кэширование стран =================
    async def get_all_countries(self) -> Dict[str, int]:
        """Возвращает словарь {название_страны: id} из кэша."""
        return await self._country_cache.get_all_items()

    async def set_country(self, country_name: str, country_id: int) -> None:
        """Добавляет страну в кэш"""

        await self._country_cache.set(country_name, country_id)

    async def get_country_id(self, country_name: str) -> Optional[int]:
        if not country_name:
            return None
        country_name = country_name.strip()

        # Прямой поиск
        cid = await self._country_cache.get(country_name)
        if cid is not None:
            return cid

        return None

    async def preload_countries(self, session: AsyncSession, column_name: str) -> None:
        """Загружает все страны из БД в кэш."""

        if self._countries_preloaded:
            logger.debug("Страны уже предзагружены")
            return

        logger.info(f"🔄 Предзагрузка стран из БД (колонка: {column_name})...")
        start = time.time()

        try:
            if not hasattr(CountryModel, column_name):
                logger.error(f"❌ Колонка '{column_name}' не найдена в CountryModel")
                return

            column = getattr(CountryModel, column_name)
            stmt = select(CountryModel.id, column)
            result = await session.execute(stmt)
            rows = result.all()

            count = 0
            for country_id, country_name in rows:
                if country_name:
                    await self.set_country(country_name, country_id)
                    count += 1

            self._countries_preloaded = True
            elapsed = time.time() - start
            logger.info(f"✅ Загружено {count} стран в кэш за {elapsed:.2f} сек")
        except Exception as e:
            logger.error(f"❌ Ошибка предзагрузки стран: {e}")
            raise

    #
    #
    #
    # ================= Кэширование городов =================
    async def get_city_id(self, country_id: int, city_name: str) -> Optional[int]:
        key = f"{country_id}_{city_name}"
        return await self._city_cache.get(key)

    async def set_city(self, country_id: int, city_name: str, city_id: int) -> None:
        key = f"{country_id}_{city_name}"
        await self._city_cache.set(key, city_id)

    #
    #
    #
    # ================= Кэширование метрик =================
    async def get_metric(self, slug: str) -> Optional[MetricInfoModel]:
        return await self._metric_cache.get(slug)

    async def set_metric(self, slug: str, metric: MetricInfoModel) -> None:
        await self._metric_cache.set(slug, metric)

    #
    #
    #
    # ================= Кэширование серий =================
    async def get_series(self, metric_id: int, attributes_hash: str) -> Optional[MetricSeriesModel]:
        return await self._series_cache.get(f"series_{metric_id}_{attributes_hash}")

    async def set_series(self, metric_id: int, attributes_hash: str, series: MetricSeriesModel) -> None:
        await self._series_cache.set(f"series_{metric_id}_{attributes_hash}", series)

    async def preload_series(self, session: AsyncSession, metric_id: int) -> None:
        """Загружает все серии указанной метрики вместе с их атрибутами,
        вычисляет хэш комбинации атрибутов и помещает в кэш.
        """

        logger.info(f"🔄 Предзагрузка серий для метрики {metric_id}...")
        start = time.time()

        stmt = (
            select(MetricSeriesModel)
            .where(MetricSeriesModel.metric_id == metric_id)
            .options(
                selectinload(MetricSeriesModel.series_attributes).joinedload(MetricSeriesAttribute.attribute_type),
                selectinload(MetricSeriesModel.series_attributes).joinedload(MetricSeriesAttribute.attribute_value),
            )
        )
        result = await session.execute(stmt)
        series_list = result.scalars().all()

        count = 0
        for series in series_list:
            # Если хэш уже есть в БД – используем его
            if str(series.attributes_hash):
                h = series.attributes_hash
            else:
                # Иначе вычисляем (для обратной совместимости)
                pairs = []
                for sa in series.series_attributes:
                    if sa.attribute_type_id and sa.attribute_value_id:
                        pairs.append((sa.attribute_type_id, sa.attribute_value_id))
                pairs.sort(key=lambda x: (x[0], x[1]))
                h = self._hash_attr_pairs(pairs)
            key = f"series_{metric_id}_{h}"
            await self._series_cache.set(key, series)
            count += 1

        elapsed = time.time() - start
        logger.info(f"✅ Предзагружено {count} серий за {elapsed:.2f} сек")

    @staticmethod
    def _hash_attr_pairs(pairs: List[Tuple[int, int]]) -> str:
        """Генерирует хэш строку из отсортированного списка пар (type_id, value_id)."""

        return "_".join(f"{t}:{v}" for t, v in pairs)

    #
    #
    #
    # ================= Кэширование периодов =================
    async def get_period(self, period_key: str) -> Optional[MetricPeriodModel]:
        return await self._period_cache.get(period_key)

    async def set_period(self, period_key: str, period: MetricPeriodModel) -> None:
        await self._period_cache.set(period_key, period)

    async def preload_periods(self, session: AsyncSession) -> None:
        """Загружает все периоды из БД и кэширует по period_key."""

        logger.info("🔄 Предзагрузка периодов с учетом конфигурации...")
        start = time.time()

        stmt = select(MetricPeriodModel).order_by(MetricPeriodModel.created_at).limit(self.config.cache.period_size)

        result = await session.execute(stmt)
        periods = result.scalars().all()

        count = 0
        for period in periods:
            key = self._make_period_key_from_model(period)
            await self._period_cache.set(key, period)
            count += 1

        elapsed = time.time() - start
        logger.info(f"✅ Предзагружено {count} периодов за {elapsed:.2f} сек")

    @staticmethod
    def _make_period_key_from_model(period: MetricPeriodModel) -> str:
        """Создаёт специальный ключ для кэширования периодов"""

        key = f"{period.period_type.value}_{period.period_year}"
        if period.period_month is not None:
            key += f"_{period.period_month}"
        if period.period_quarter is not None:
            key += f"_q{period.period_quarter}"
        if period.period_week is not None:
            key += f"_w{period.period_week}"
        return key

    #
    #
    #
    # ================= Кэширование типов атрибутов =================
    async def get_attribute_type(self, code: str) -> Optional[MetricAttributeTypeModel]:
        return await self._attr_type_cache.get(code)

    async def set_attribute_type(self, attr_type: MetricAttributeTypeModel) -> None:
        await self._attr_type_cache.set(attr_type.code, attr_type)

    async def preload_attribute_types(self, session: AsyncSession) -> None:
        """Загружает все типы атрибутов из БД и помещает в кэш (ключ – code)."""
        logger.info("🔄 Предзагрузка типов атрибутов...")
        start = time.time()

        stmt = select(MetricAttributeTypeModel)
        result = await session.execute(stmt)
        types = result.scalars().all()

        count = 0
        for attr_type in types:
            await self._attr_type_cache.set(attr_type.code, attr_type)
            count += 1

        elapsed = time.time() - start
        logger.info(f"✅ Предзагружено {count} типов атрибутов за {elapsed:.2f} сек")

    #
    #
    #
    # ================= Кэширование значений атрибутов =================
    async def get_attribute_value(self, type_id: int, value_code: str) -> Optional[MetricAttributeValueModel]:
        key = (type_id, value_code)
        return await self._attr_value_cache.get(key)

    async def set_attribute_value(self, type_id: int, value: MetricAttributeValueModel) -> None:
        key = (type_id, value.code)
        await self._attr_value_cache.set(key, value)

    async def preload_attribute_values(self, session: AsyncSession) -> None:
        """Загружает все значения атрибутов и помещает в кэш (ключ – (type_id, code))."""

        logger.info("🔄 Предзагрузка значений атрибутов...")
        start = time.time()

        stmt = select(MetricAttributeValueModel)
        result = await session.execute(stmt)
        values = result.scalars().all()

        count = 0
        for val in values:
            await self._attr_value_cache.set((val.attribute_type_id, val.code), val)
            count += 1

        elapsed = time.time() - start
        logger.info(f"✅ Предзагружено {count} значений атрибутов за {elapsed:.2f} сек")
