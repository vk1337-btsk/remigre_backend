# etl/universal/service_db_etl.py
"""
Сервис для работы с базой данных в ETL
"""
import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple, cast

from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from etl.universal.config_schema import (
    AttributeConfig,
    AttributeParsingStrategyEnum,
    AttributeTypeDTO,
    AttributeValueDTO,
    ComplexParseResultDTO,
    ETLConfig,
    FieldSourceDTO,
    FieldSourceTypeEnum,
    MetricConfig,
    ParsedAttributeDTO,
    PeriodConfig,
    PeriodDataDTO,
)
from etl.universal.lru_caches import LRUCache
from src.core.config.logging import setup_logger_to_file
from src.core.enums import TypeDataEnum
from src.ms_location.models import CityModel, CountryModel
from src.ms_metric.models import (
    MetricAttributeTypeModel,
    MetricAttributeValueModel,
    MetricDataNewModel,
    MetricInfoNewModel,
    MetricPeriodNewModel,
    MetricSeriesAttribute,
    MetricSeriesNewModel,
)


logger = setup_logger_to_file()


class DB_ServiceUniversalETL:
    """Сервис для работы с базой данных в ETL"""

    def __init__(self, session: AsyncSession, config: ETLConfig):
        self.session = session
        self.config = config

        # Инициализируем LRU кэши с разумными размерами
        self._country_cache = LRUCache(maxsize=self.config.cache.country_size, name=self.config.cache.country_name)
        self._city_cache = LRUCache(maxsize=self.config.cache.city_size, name=self.config.cache.city_name)
        self._metric_cache = LRUCache(maxsize=self.config.cache.metric_size, name=self.config.cache.metric_name)
        self._series_cache = LRUCache(maxsize=self.config.cache.series_size, name=self.config.cache.series_name)
        self._period_cache = LRUCache(maxsize=self.config.cache.period_size, name=self.config.cache.period_name)

        # Для attribute_value_cache используем Tuple[int, str] как ключ
        self._attribute_type_cache = LRUCache(
            maxsize=self.config.cache.attribute_type_size, name=self.config.cache.attribute_type_name
        )
        self._attribute_value_cache = LRUCache(
            maxsize=self.config.cache.attribute_value_size, name=self.config.cache.attribute_value_name
        )

        # Флаг предзагрузки стран
        self._countries_preloaded = False

        # Статистика
        self.stats = {"duplicates_skipped": 0, "new_records": 0, "cache_stats": {}}

    #
    #
    # ============ ОБЩИЕ МЕТОДЫ для КЭША ============
    def _get_cache_key_for_attribute_value(self, attr_type_id: int, value_code: str) -> Tuple[int, str]:
        """Генерирует ключ для кэша значений атрибутов"""

        return (attr_type_id, value_code)

    async def _clear_caches_after_rollback(self):
        """Очищает кэши после отката транзакции"""

        logger.info("Очистка кэшей после отката транзакции...")

        # Очищаем все кэши
        self._attribute_type_cache.clear()
        self._attribute_value_cache.clear()
        self._series_cache.clear()
        self._period_cache.clear()

        logger.info("Кэши очищены")

    async def clear_all_caches(self):
        """Очищает все кэши"""
        logger.info("🧹 Очистка всех кэшей...")

        self._country_cache.clear()
        self._city_cache.clear()
        self._metric_cache.clear()
        self._series_cache.clear()
        self._period_cache.clear()
        self._attribute_type_cache.clear()
        self._attribute_value_cache.clear()

        self._countries_preloaded = False
        logger.info("✅ Все кэши очищены")

    async def _update_cache_stats(self):
        """Обновляет статистику кэшей"""

        self.stats["cache_stats"] = {
            "country_cache": self._country_cache.stats(),
            "city_cache": self._city_cache.stats(),
            "metric_cache": self._metric_cache.stats(),
            "series_cache": self._series_cache.stats(),
            "period_cache": self._period_cache.stats(),
            "attribute_type_cache": self._attribute_type_cache.stats(),
            "attribute_value_cache": self._attribute_value_cache.stats(),
        }

    async def log_cache_stats(self):
        """Логирует статистику кэшей"""

        await self._update_cache_stats()

        logger.debug("\n📊 СТАТИСТИКА КЭШЕЙ:")
        for _, stats in self.stats["cache_stats"].items():
            logger.debug(f"  {stats['name']}:")
            logger.debug(f"    Размер: {stats['size']}/{stats['maxsize']} ({stats['fullness']})")
            logger.debug(f"    Попадания: {stats['hits']}, Промахи: {stats['misses']}")
            logger.debug(f"    Эффективность: {stats['hit_rate']}")
            if stats["evictions"] > 0:
                logger.debug(f"    Вытеснено: {stats['evictions']}")

    #
    #
    # ============ ОБЩИЕ МЕТОДЫ ============
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _execute_with_retry(self, stmt):
        """Выполнить запрос с ретраями"""

        try:
            # logger.debug(f"Выполнение SQL: {stmt}")
            result = await self.session.execute(stmt)
            return result

        except Exception as e:
            logger.error(f"Ошибка при выполнении SQL: {e}")

            # Если транзакция прервана, пробуем откатить и продолжить
            if "current transaction is aborted" in str(e) or "InFailedSQLTransactionError" in str(e):
                logger.warning("Транзакция прервана, пытаемся восстановить...")

                try:
                    await self.session.rollback()

                    await self._clear_caches_after_rollback()  # ОЧИЩАЕМ КЭШ ПОСЛЕ ОТКАТА

                    logger.info("Транзакция откачена, кэш очищен, повторяем запрос...")
                except Exception as rollback_error:
                    logger.error(f"Ошибка при откате транзакции: {rollback_error}")

            raise

    async def bulk_insert_metric_data(self, records: List[MetricDataNewModel]) -> int:
        """Быстрая массовая вставка с защитой от дубликатов (использует индекс с COALESCE)"""

        logger.debug(f"Bulk insert {len(records)} записей...")

        if not records:
            return 0

        try:
            # 1. Создаем временную таблицу
            await self.session.execute(
                text(
                    """
                CREATE TEMP TABLE temp_metric_data (
                    series_id INTEGER,
                    period_id INTEGER,
                    country_id INTEGER,
                    city_id INTEGER,
                    value_numeric NUMERIC,
                    value_string VARCHAR,
                    value_boolean BOOLEAN,
                    value_range_start NUMERIC,
                    value_range_end NUMERIC,
                    meta_data JSONB,
                    created_at TIMESTAMPTZ,
                    updated_at TIMESTAMPTZ
                ) ON COMMIT DROP
            """
                )
            )

            # 2. Вставляем все записи во временную таблицу
            values_list = []
            for record in records:
                values_list.append(
                    {
                        "series_id": record.series_id,
                        "period_id": record.period_id,
                        "country_id": record.country_id,
                        "city_id": record.city_id,
                        "value_numeric": record.value_numeric,
                        "value_string": record.value_string,
                        "value_boolean": record.value_boolean,
                        "value_range_start": record.value_range_start,
                        "value_range_end": record.value_range_end,
                        "meta_data": record.meta_data,
                        "created_at": record.created_at,
                        "updated_at": record.updated_at,
                    }
                )

            # 3. Вставляем батчем во временную таблицу
            insert_temp = text(
                """
                INSERT INTO temp_metric_data 
                VALUES (:series_id, :period_id, :country_id, :city_id,
                        :value_numeric, :value_string, :value_boolean,
                        :value_range_start, :value_range_end,
                        :meta_data, :created_at, :updated_at)
            """
            )

            await self.session.execute(insert_temp, values_list)

            # 4. Вставляем из временной таблицы в основную, избегая дубликатов
            insert_stmt = text(
                """
                INSERT INTO metric_data_new 
                (series_id, period_id, country_id, city_id,
                value_numeric, value_string, value_boolean,
                value_range_start, value_range_end,
                meta_data, created_at, updated_at)
                SELECT 
                    series_id, period_id, country_id, city_id,
                    value_numeric, value_string, value_boolean,
                    value_range_start, value_range_end,
                    meta_data, created_at, updated_at
                FROM temp_metric_data t
                WHERE NOT EXISTS (
                    SELECT 1 
                    FROM metric_data_new m
                    WHERE m.series_id = t.series_id
                    AND m.country_id = t.country_id
                    AND m.period_id = t.period_id
                    AND COALESCE(m.city_id, -1) = COALESCE(t.city_id, -1)
                )
            """
            )

            result = await self.session.execute(insert_stmt)
            total_inserted = result.rowcount

            await self.session.commit()

            logger.info(f"✅ Вставлено {total_inserted} уникальных записей из {len(records)}")
            self.stats["duplicates_skipped"] = len(records) - total_inserted
            self.stats["new_records"] = total_inserted

            logger.debug(f"Bulk insert {len(records)} записей...")

            return total_inserted

        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Ошибка bulk insert: {e}")
            await self._clear_caches_after_rollback()
            raise

    #
    #
    # ============ ОБРАБОТКА АТРИБУТОВ ============
    async def _parse_attribute(
        self, row: Dict[str, str], attr_config: AttributeConfig
    ) -> Tuple[List[ParsedAttributeDTO], Optional[PeriodDataDTO]]:
        """Парсит атрибут в зависимости от стратегии"""

        value = row.get(attr_config.csv_column)

        if not value:
            return [], None

        # Если стратегия фиксированная
        if attr_config.parsing_strategy == AttributeParsingStrategyEnum.FIXED_TYPE:

            assert attr_config.attribute_type_code is not None  # Обязательно будут заданы
            assert attr_config.attribute_type_name is not None  # Обязательно будут заданы

            attribute = ParsedAttributeDTO(
                type=AttributeTypeDTO(
                    code=attr_config.attribute_type_code,
                    name=attr_config.attribute_type_name,
                    value_type=attr_config.def_type_value_type,
                    is_active=attr_config.def_type_is_active,
                    is_filtered=attr_config.def_type_is_filtered,
                    sort_order=attr_config.def_type_sort_order,
                    meta_data=attr_config.def_type_meta_data,
                ),
                value=AttributeValueDTO(
                    code=value,
                    name=value,
                    is_active=attr_config.def_value_is_active,
                    is_filtered=attr_config.def_value_is_filtered,
                    sort_order=attr_config.def_value_sort_order,
                    meta_data=attr_config.def_value_meta_data,
                ),
            )
            return [attribute], None

        # Если стратегия кастомная
        elif attr_config.parsing_strategy == AttributeParsingStrategyEnum.CUSTOM:

            if not attr_config.custom_parser:
                logger.error("❌ Для CUSTOM стратегии должен быть задан custom_parser")
                raise ValueError("❌ Для CUSTOM стратегии должен быть задан custom_parser")

            result = attr_config.custom_parser(value)

            if isinstance(result, ParsedAttributeDTO):
                return [result], None
            else:
                logger.error(f"❌ Кастомный парсер вернул неподдерживаемый тип: {type(result)}")
                return [], None

        # Если стратегия комплексная
        elif attr_config.parsing_strategy == AttributeParsingStrategyEnum.COMPLEX:

            if not attr_config.complex_parser:
                logger.error("❌ Для COMPLEX стратегии должен быть задан complex_parser")
                raise ValueError("❌ Для COMPLEX стратегии должен быть задан complex_parserr")

            result = attr_config.complex_parser(value)

            if isinstance(result, ComplexParseResultDTO):
                return result.attributes, result.period_data
            else:
                logger.error(f"❌ Complex parser вернул неверный тип: {type(result)}")
                return [], None

        logger.error(f"Неизвестная стратегия парсинга: {row=}, {attr_config.parsing_strategy=}")
        return [], None

    async def get_or_create_attribute_type(self, parsed_attr: ParsedAttributeDTO) -> MetricAttributeTypeModel:
        """Получает или создает тип атрибута с LRU кэшированием"""

        type_code = parsed_attr.type.code

        # Проверяем кэш
        cached_type = self._attribute_type_cache.get(type_code)
        if cached_type:
            return cached_type

        # Ищем в БД
        stmt = select(MetricAttributeTypeModel).where(MetricAttributeTypeModel.code == type_code)
        result = await self._execute_with_retry(stmt)
        attr_type = result.scalar_one_or_none()

        if not attr_type:
            # Создаем новый тип атрибута
            attr_type = MetricAttributeTypeModel(
                code=parsed_attr.type.code,
                name=parsed_attr.type.name,
                value_type=parsed_attr.type.value_type,
                is_filtered=parsed_attr.type.is_filtered,
                sort_order=parsed_attr.type.sort_order,
                is_active=parsed_attr.type.is_active,
                meta_data=parsed_attr.type.meta_data,
            )
            self.session.add(attr_type)
            await self.session.flush()

        # Сохраняем в кэш
        self._attribute_type_cache.set(type_code, attr_type)
        return attr_type

    async def get_or_create_attribute_value(
        self, attr_type: MetricAttributeTypeModel, parsed_attr: ParsedAttributeDTO
    ) -> MetricAttributeValueModel:
        """Получает или создает значение атрибута с LRU кэшированием"""

        cache_key = self._get_cache_key_for_attribute_value(cast(int, attr_type.id), parsed_attr.value.code)

        # Проверяем кэш
        cached_value = self._attribute_value_cache.get(cache_key)
        if cached_value:
            return cached_value

        # Ищем в БД
        stmt = select(MetricAttributeValueModel).where(
            MetricAttributeValueModel.attribute_type_id == attr_type.id,
            MetricAttributeValueModel.code == parsed_attr.value.code,
        )
        result = await self._execute_with_retry(stmt)
        attr_value = result.scalar_one_or_none()

        if not attr_value:
            # Создаем новое значение атрибута
            attr_value = MetricAttributeValueModel(
                attribute_type_id=attr_type.id,
                code=parsed_attr.value.code,
                name=parsed_attr.value.name,
                is_active=parsed_attr.value.is_active,
                is_filtered=parsed_attr.value.is_filtered,
                sort_order=parsed_attr.value.sort_order,
                meta_data=parsed_attr.value.meta_data,
            )
            self.session.add(attr_value)
            await self.session.flush()

        # Сохраняем в кэш
        self._attribute_value_cache.set(cache_key, attr_value)
        return attr_value

    async def process_attributes(
        self, row: Dict[str, str], attributes_config: List[AttributeConfig]
    ) -> Tuple[List[Tuple[MetricAttributeTypeModel, MetricAttributeValueModel]], Optional[PeriodDataDTO]]:
        """Обрабатывает все атрибуты строки"""
        # start = time.time()
        all_attributes = []
        complex_period_data = None

        for attr_config in attributes_config:
            try:

                attributes, period_data = await self._parse_attribute(row, attr_config)

                for parsed_attr in attributes:
                    attr_type = await self.get_or_create_attribute_type(parsed_attr)
                    attr_value = await self.get_or_create_attribute_value(attr_type, parsed_attr)
                    all_attributes.append((attr_type, attr_value))

                if period_data and not complex_period_data:
                    complex_period_data = period_data

            except Exception as e:
                logger.error(f"❌ Ошибка парсинга атрибута {attr_config.csv_column}: {e}")
                logger.error(f"   Значение: {row.get(attr_config.csv_column, '')}")
                logger.error(f"   Строка: {row}")
                raise

        # logger.debug(f"parse_attributes для строки: {time.time() - start}")
        return all_attributes, complex_period_data

    #
    #
    # ============ ГЕОГРАФИЧЕСКИЕ ОБЪЕКТЫ ============
    async def get_country_id(
        self, country_name: str, country_mapping: Dict[str, List[str]], column_name: str
    ) -> Optional[int]:
        """Получает ID страны с учетом маппинга, LRU кэширования и предзагрузки"""

        # logger.debug(f"Поиск страны: {country_name}")
        if not country_name:
            return None

        original_name = country_name.strip()

        # 1. Сначала проверяем кэш (быстрее всего)
        cached_id = self._country_cache.get(original_name)
        if cached_id is not None:
            return cached_id

        # 3. Проверяем маппинг (ключ - название из CSV)
        if original_name in country_mapping:
            db_names = country_mapping[original_name]

            # Пробуем каждое название из списка
            for db_name in db_names:
                # Сначала проверяем кэш для db_name
                cached_id = self._country_cache.get(db_name)
                if cached_id is not None:
                    # Сохраняем маппинг для оригинального названия
                    self._country_cache.set(original_name, cached_id)
                    logger.debug(f"Маппинг из кэша: '{original_name}' → '{db_name}' → ID: {cached_id}")
                    return cached_id

                # Проверяем lowercase версию db_name
                lower_db_name = db_name.lower()
                cached_id = self._country_cache.get(lower_db_name)
                if cached_id is not None:
                    self._country_cache.set(original_name, cached_id)
                    self._country_cache.set(db_name, cached_id)
                    logger.debug(f"Маппинг из кэша (lowercase): '{original_name}' → '{db_name}' → ID: {cached_id}")
                    return cached_id

            # Если не нашли в кэше, ищем в БД для первого db_name
            if db_names and hasattr(CountryModel, column_name):
                db_name = db_names[0]
                column = getattr(CountryModel, column_name)
                stmt = select(CountryModel).where(column == db_name)
                result = await self._execute_with_retry(stmt)
                country = result.scalar_one_or_none()

                if country:
                    # Сохраняем в кэш для всех вариантов
                    self._country_cache.set(original_name, country.id)
                    self._country_cache.set(db_name, country.id)
                    self._country_cache.set(db_name.lower(), country.id)

                    logger.debug(f"Маппинг из БД: '{original_name}' → '{db_name}' → ID: {country.id}")
                    return country.id

            logger.warning(f"Для страны '{original_name}' не найдено ни одного соответствия в БД из списка: {db_names}")
            return None

        # 4. Если маппинга нет и не нашли в кэше, ищем в БД
        if hasattr(CountryModel, column_name):
            column = getattr(CountryModel, column_name)
            stmt = select(CountryModel).where(column == original_name)
            result = await self._execute_with_retry(stmt)
            country = result.scalar_one_or_none()

            if country:
                # Сохраняем в кэш
                self._country_cache.set(original_name, country.id)
                return country.id

        logger.debug(f"Страна не найдена ни в кэше, ни в БД: '{original_name}'")
        return None

    async def get_city_id(self, city_name: str, country_id: int, city_mapping: Dict[str, List[str]]) -> Optional[int]:
        """Получает ID города с учетом маппинга"""

        if not city_name or not country_id:
            return None

        # Проверяем маппинг
        for mapped_name, variations in city_mapping.items():
            if city_name in variations:
                city_name = mapped_name
                break

        # Поиск города в кэше
        cached_city_id = self._city_cache.get(f"{country_id}_{city_name}")
        if cached_city_id is not None:
            return cached_city_id

        # Ищем в БД
        stmt = select(CityModel).where(and_(CityModel.country_id == country_id, CityModel.name_eng == city_name))
        result = await self._execute_with_retry(stmt)
        city = result.scalar_one_or_none()

        if city:
            # Добавляем в кэш
            self._city_cache.set(f"{country_id}_{city_name}", cast(int, city.id))
            return cast(int, city.id)

        logger.warning(f"Город не найден: {city_name} для страны ID: {country_id}")
        return None

    async def _get_all_countries_from_db(self) -> Dict[str, int]:
        """Получает все страны из БД в виде словаря {name_eng: id}"""

        try:

            stmt = select(CountryModel.name_eng, CountryModel.id)
            result = await self.session.execute(stmt)
            countries = result.all()

            return {name_eng: country_id for name_eng, country_id in countries}

        except Exception as e:
            logger.error(f"Ошибка при получении списка стран из БД: {e}")
            return {}

    #
    #
    # ============ МЕТРИКИ И СЕРИИ ============
    async def get_or_create_metric(self, metric_config: MetricConfig) -> MetricInfoNewModel:
        """Получает или создает метрику"""

        logger.debug(f"Поиск метрики по slug: '{metric_config.slug}'")

        # Поиск метрики в кэше
        cached_metric = self._metric_cache.get(metric_config.slug)
        if cached_metric:
            logger.debug(f"Метрика найдена в кэше: {metric_config.slug}")
            return cached_metric

        stmt = select(MetricInfoNewModel).where(MetricInfoNewModel.slug == metric_config.slug)
        logger.debug(f"Выполнение запроса для метрики: {metric_config.slug}")

        try:
            result = await self._execute_with_retry(stmt)
            metric = result.scalar_one_or_none()

            if not metric:
                logger.info(f"Метрика не найдена, создаем новую: {metric_config.name}")
                metric = MetricInfoNewModel(
                    slug=metric_config.slug,
                    name=metric_config.name,
                    description=metric_config.description,
                    category=metric_config.category,
                    data_type=metric_config.data_type.value,
                    source_name=metric_config.source_name,
                    source_url=metric_config.source_url,
                    show_in_country_list=metric_config.show_in_country_list,
                    show_in_country_detail=metric_config.show_in_country_detail,
                    show_in_city_list=metric_config.show_in_city_list,
                    show_in_city_detail=metric_config.show_in_city_detail,
                    list_priority=metric_config.list_priority,
                    detail_priority=metric_config.detail_priority,
                    is_primary=metric_config.is_primary,
                    is_secondary=metric_config.is_secondary,
                    meta_data=metric_config.meta_data,
                    is_active=metric_config.is_active,
                )
                self.session.add(metric)

                try:
                    await self.session.flush()
                    logger.info(f"✅ Метрика создана: {metric_config.name} (ID: {metric.id})")

                except Exception as flush_error:
                    logger.error(f"❌ Ошибка при создании метрики: {flush_error}")
                    logger.error(f"Тип ошибки: {type(flush_error).__name__}")
                    await self.session.rollback()
                    raise
            else:
                logger.info(f"✅ Метрика найдена в БД: {metric.name} (ID: {metric.id})")

            self._metric_cache.set(metric_config.slug, metric)
            return metric

        except Exception as e:
            logger.error(f"❌ Критическая ошибка в get_or_create_metric: {e}")
            logger.error(f"Тип ошибки: {type(e).__name__}")
            raise

    async def get_or_create_series(
        self,
        metric_id: int,
        attributes: List[Tuple[MetricAttributeTypeModel, MetricAttributeValueModel]],
        series_metadata: Optional[Dict[str, Any]] = None,
    ) -> MetricSeriesNewModel:
        """Получает или создает серию с LRU кэшированием"""

        start = time.time()

        # Создаем ключ для кэша
        attr_parts = []
        for attr_type, attr_value in sorted(attributes, key=lambda x: (x[0].code, x[1].code)):
            attr_parts.append(f"{attr_type.id}:{attr_value.id}")

        cache_key = f"series_{metric_id}_{'_'.join(attr_parts)}"

        # Проверяем кэш
        cached_series = self._series_cache.get(cache_key)
        if cached_series:
            return cached_series

        # 1. Ищем существующую серию по комбинации атрибутов
        existing_series = await self._find_series_by_attributes(metric_id, attributes)

        if existing_series:
            self._series_cache.set(cache_key, existing_series)
            return existing_series

        # 2. Создаем новую серию
        series = MetricSeriesNewModel(metric_id=metric_id, is_active=True, is_preset=False, meta_data=series_metadata)
        self.session.add(series)
        await self.session.flush()

        # 3. Создаем связи с атрибутами
        for attr_type, attr_value in attributes:
            series_attr = MetricSeriesAttribute(
                series_id=series.id,
                attribute_type_id=attr_type.id,
                attribute_value_id=attr_value.id,
                is_primary=True,
                is_filtered=None,
                sort_order=0,
            )
            self.session.add(series_attr)

        await self.session.flush()

        # Сохраняем в кэш
        self._series_cache.set(cache_key, series)
        # logger.debug(f"get_or_create_series: {time.time() - start}")

        return series

    async def _find_series_by_attributes(
        self, metric_id: int, attributes: List[Tuple[MetricAttributeTypeModel, MetricAttributeValueModel]]
    ) -> Optional[MetricSeriesNewModel]:
        """Находит серию по комбинации атрибутов"""

        if not attributes:
            return None

        # Для каждой пары атрибутов создаем условие
        attribute_conditions = []
        for attr_type, attr_value in attributes:
            subquery = (
                select(MetricSeriesAttribute.series_id)
                .where(
                    MetricSeriesAttribute.attribute_type_id == attr_type.id,
                    MetricSeriesAttribute.attribute_value_id == attr_value.id,
                )
                .scalar_subquery()
            )
            attribute_conditions.append(subquery)

        # Ищем серии, которые имеют ВСЕ указанные атрибуты
        # и имеют ровно столько атрибутов, сколько указано
        series_stmt = (
            select(MetricSeriesNewModel)
            .join(MetricSeriesAttribute, MetricSeriesNewModel.id == MetricSeriesAttribute.series_id)
            .where(
                MetricSeriesNewModel.metric_id == metric_id,
                *[MetricSeriesNewModel.id.in_(condition) for condition in attribute_conditions],
            )
            .group_by(MetricSeriesNewModel.id)
            .having(func.count(MetricSeriesAttribute.id) == len(attributes))
        )

        result = await self._execute_with_retry(series_stmt)
        return result.scalar_one_or_none()

    #
    #
    # ============ ПЕРИОДЫ============
    async def get_or_create_period(
        self,
        series_id: int,
        period_config: PeriodConfig,
        row: Dict[str, str],
        complex_period_data: Optional[PeriodDataDTO] = None,
    ) -> MetricPeriodNewModel:
        """Получает или создает период с LRU кэшированием"""

        # Собираем данные периода
        period_dto = await self._collect_period_data(period_config, row, complex_period_data)

        # Ключ для кэша периодов
        cache_key = f"{series_id}_{period_config.period_type}_{period_dto.period_year}"
        if period_dto.period_month:
            cache_key += f"_{period_dto.period_month}"
        if period_dto.period_quarter:
            cache_key += f"_q{period_dto.period_quarter}"
        if period_dto.period_week:
            cache_key += f"_w{period_dto.period_week}"

        # Проверяем кэш
        cached_period = self._period_cache.get(cache_key)
        if cached_period:
            return cached_period

        # Ищем существующий период в БД
        stmt = select(MetricPeriodNewModel).where(
            and_(
                MetricPeriodNewModel.series_id == series_id,
                MetricPeriodNewModel.period_type == period_config.period_type.value,
                MetricPeriodNewModel.period_year == period_dto.period_year,
                MetricPeriodNewModel.period_month == period_dto.period_month,
                MetricPeriodNewModel.period_quarter == period_dto.period_quarter,
                MetricPeriodNewModel.period_week == period_dto.period_week,
            )
        )
        result = await self._execute_with_retry(stmt)
        period = result.scalar_one_or_none()

        if not period:
            # Создаем новый период
            period = MetricPeriodNewModel(
                series_id=series_id,
                period_type=period_config.period_type.value,
                period_year=period_dto.period_year,
                period_month=period_dto.period_month,
                period_quarter=period_dto.period_quarter,
                period_week=period_dto.period_week,
                date_start=period_dto.date_start,
                date_end=period_dto.date_end,
                collected_at=period_dto.collected_at,
                meta_data=period_dto.meta_data,
                is_active=True,
            )
            self.session.add(period)
            await self.session.flush()

        # Сохраняем в кэш периодов
        self._period_cache.set(cache_key, period)
        return period

    async def _collect_period_data(
        self, period_config: PeriodConfig, row: Dict[str, str], complex_period_data: Optional[PeriodDataDTO] = None
    ) -> PeriodDataDTO:
        """Собирает данные периода из разных источников"""

        # Собираем данные в словарь
        period_dict: Dict[str, Any] = {}

        # Сначала берем данные из complex_parser (если передан DTO)
        if complex_period_data:
            # Преобразуем DTO в словарь (без None значений)
            period_dict.update(complex_period_data.model_dump(exclude_none=True))

        # Затем заполняем из конфигурации (если не заполнено)
        fields_mapping: dict[str, Optional[FieldSourceDTO]] = {
            "period_year": period_config.period_year,
            "period_month": period_config.period_month,
            "period_quarter": period_config.period_quarter,
            "period_week": period_config.period_week,
            "date_start": period_config.date_start,
            "date_end": period_config.date_end,
            "collected_at": period_config.collected_at,
        }

        for field_name, field_source in fields_mapping.items():
            if field_source and field_name not in period_dict:
                value = await self._get_field_value(field_source, row)
                if value is not None:
                    period_dict[field_name] = value

        # Создаем DTO
        try:
            period_dto = PeriodDataDTO(
                period_year=period_dict.get("period_year"),
                period_month=period_dict.get("period_month"),
                period_quarter=period_dict.get("period_quarter"),
                period_week=period_dict.get("period_week"),
                date_start=period_dict.get("date_start"),
                date_end=period_dict.get("date_end"),
                collected_at=period_dict.get("collected_at"),
                meta_data=period_dict.get("meta_data"),
            )
            return period_dto

        except Exception as e:
            logger.error(f"Ошибка создания PeriodDataDTO: {e}")
            logger.error(f"Данные: {period_dict}")
            raise

    async def _get_field_value(self, field_source: FieldSourceDTO, row: Dict[str, str]) -> Any:
        """Получает значение поля из источника"""

        if field_source.source_type == FieldSourceTypeEnum.COLUMN:
            value = row.get(field_source.column_name or "", "").strip()
            if field_source.transform_callback:
                value = field_source.transform_callback(value)
            return value if value else None

        elif field_source.source_type == FieldSourceTypeEnum.FIXED:
            return field_source.fixed_value

        elif field_source.source_type == FieldSourceTypeEnum.CALLBACK and field_source.callback:
            return field_source.callback(row)

        return None

    #
    #
    # ============ ДАННЫЕ МЕТРИК============
    async def create_metric_data(
        self,
        series_id: int,
        period_id: int,
        country_id: int,
        city_id: Optional[int],
        value: str,
        data_type: TypeDataEnum,
    ) -> Optional[MetricDataNewModel]:
        """Создает запись данных метрики с проверкой дубликатов"""

        # Преобразуем значение
        value_numeric = None
        value_string = None
        value_boolean = None
        value_range_start = None
        value_range_end = None

        try:
            if data_type == TypeDataEnum.FLOAT:
                value_numeric = float(value.replace(",", ".")) if value else None
            elif data_type == TypeDataEnum.STRING:
                value_string = str(value) if value else None
            elif data_type == TypeDataEnum.BOOL:
                value_boolean = value.lower() in ["true", "yes", "1", "да"] if value else None
            elif data_type == TypeDataEnum.RANGE:
                if value and "-" in value:
                    parts = value.split("-")
                    if len(parts) == 2:
                        value_range_start = float(parts[0].replace(",", ".")) if parts[0] else None
                        value_range_end = float(parts[1].replace(",", ".")) if parts[1] else None
        except (ValueError, AttributeError) as e:
            logger.warning(f"Не удалось преобразовать значение '{value}': {e}")
            return None

        # Создаем объект (но не добавляем в сессию!)
        data_record = MetricDataNewModel(
            series_id=series_id,
            period_id=period_id,
            country_id=country_id,
            city_id=city_id,
            value_numeric=value_numeric,
            value_string=value_string,
            value_boolean=value_boolean,
            value_range_start=value_range_start,
            value_range_end=value_range_end,
        )

        return data_record

    #
    #
    # ============ ПРЕДЗАГРУЗКА ДАННЫХ ============
    async def preload_countries(self, column_name: str):
        """Предзагружает все страны из БД в кэш"""

        if self._countries_preloaded:
            logger.debug("Страны уже предзагружены")
            return

        logger.debug(f"🔄 Предзагрузка стран из БД (колонка: {column_name})...")
        start_time = asyncio.get_event_loop().time()

        try:
            # Проверяем, существует ли колонка
            if not hasattr(CountryModel, column_name):
                logger.error(f"❌ Колонка '{column_name}' не найдена в CountryModel")
                return

            # Получаем все страны
            column = getattr(CountryModel, column_name)
            stmt = select(CountryModel.id, column)
            result = await self._execute_with_retry(stmt)
            countries = result.all()

            # Загружаем в кэш
            count = 0
            for country_id, country_name in countries:
                if country_name:  # Проверяем, что название не пустое
                    self._country_cache.set(country_name, country_id)
                    count += 1

            # Также загружаем в lowercase для case-insensitive поиска
            for country_id, country_name in countries:
                if country_name:
                    lower_name = country_name.lower()
                    self._country_cache.set(lower_name, country_id)
                    count += 1

            elapsed = asyncio.get_event_loop().time() - start_time
            self._countries_preloaded = True

            logger.info(f"✅ Предзагружено {count} записей стран в кэш за {elapsed:.2f} сек")
            logger.info(f"   Размер кэша стран: {self._country_cache.size()}/{self._country_cache.maxsize}")

        except Exception as e:
            logger.error(f"❌ Ошибка при предзагрузке стран: {e}")
            import traceback

            logger.error(f"Трейсбэк: {traceback.format_exc()}")
            # Не прерываем выполнение, продолжаем без предзагрузки

    async def preload_attribute_types(self):
        """Предзагружает типы атрибутов из БД в кэш"""

        logger.info("🔄 Предзагрузка типов атрибутов из БД...")

        start_time = asyncio.get_event_loop().time()

        try:
            stmt = select(MetricAttributeTypeModel)
            result = await self._execute_with_retry(stmt)
            attribute_types = result.scalars().all()

            count = 0
            for attr_type in attribute_types:
                self._attribute_type_cache.set(attr_type.code, attr_type)
                count += 1

            elapsed = asyncio.get_event_loop().time() - start_time
            logger.info(f"✅ Предзагружено {count} типов атрибутов в кэш за {elapsed:.2f} сек")

        except Exception as e:
            logger.error(f"❌ Ошибка при предзагрузке типов атрибутов: {e}")

    async def preload_attribute_values(self):
        """Предзагружает часто используемые значения атрибутов"""

        logger.info("🔄 Предзагрузка значений атрибутов из БД...")
        start_time = asyncio.get_event_loop().time()

        try:
            # Получаем все значения атрибутов
            stmt = select(MetricAttributeValueModel)
            result = await self._execute_with_retry(stmt)
            attribute_values = result.scalars().all()

            count = 0
            for attr_value in attribute_values:
                cache_key = self._get_cache_key_for_attribute_value(
                    cast(int, attr_value.attribute_type_id), attr_value.code
                )
                self._attribute_value_cache.set(cache_key, attr_value)
                count += 1

            elapsed = asyncio.get_event_loop().time() - start_time
            logger.info(f"✅ Предзагружено {count} значений атрибутов в кэш за {elapsed:.2f} сек")

        except Exception as e:
            logger.error(f"❌ Ошибка при предзагрузке значений атрибутов: {e}")

    async def preload_series_for_metric(self, metric_id: int, batch_size: int = 1000):
        """Предзагружает серии для конкретной метрики с пагинацией"""

        logger.info(f"🔄 Предзагрузка серий для метрики ID: {metric_id}...")
        start_time = asyncio.get_event_loop().time()
        total_loaded = 0

        try:
            # Сначала получаем общее количество серий для метрики
            count_stmt = select(func.count(MetricSeriesNewModel.id)).where(MetricSeriesNewModel.metric_id == metric_id)
            count_result = await self._execute_with_retry(count_stmt)
            total_series = count_result.scalar()

            logger.info(f"📊 Всего серий для загрузки: {total_series}")

            if total_series == 0:
                logger.info(f"✅ Нет серий для метрики {metric_id}")
                return

            # Загружаем пачками
            offset = 0
            while offset < total_series:
                # Получаем пачку серий
                stmt = (
                    select(MetricSeriesNewModel)
                    .where(MetricSeriesNewModel.metric_id == metric_id)
                    .order_by(MetricSeriesNewModel.id)
                    .offset(offset)
                    .limit(batch_size)
                )

                result = await self._execute_with_retry(stmt)
                series_list = result.scalars().all()

                if not series_list:
                    break

                # Получаем ID всех серий в пачке
                series_ids = [series.id for series in series_list]

                # Получаем все атрибуты для всех серий в пачке одним запросом
                attr_stmt = select(MetricSeriesAttribute).where(MetricSeriesAttribute.series_id.in_(series_ids))
                attr_result = await self._execute_with_retry(attr_stmt)
                all_attributes = attr_result.scalars().all()

                # Группируем атрибуты по series_id для быстрого доступа
                attributes_by_series = {}
                for attr in all_attributes:
                    attributes_by_series.setdefault(attr.series_id, []).append(attr)

                # Обрабатываем каждую серию в пачке
                for series in series_list:
                    # Проверяем, есть ли еще место в кэше
                    if self._series_cache.size() >= self._series_cache.maxsize:
                        logger.warning(
                            f"⚠️  Достигнут лимит кэша ({self._series_cache.maxsize} записей). Остановка предзагрузки."
                        )
                        elapsed = asyncio.get_event_loop().time() - start_time
                        logger.info(f"✅ Загружено {total_loaded} из {total_series} серий за {elapsed:.2f} сек")
                        return

                    # Получаем атрибуты для текущей серии
                    series_attrs = attributes_by_series.get(series.id, [])

                    # Создаем список пар (type_id, value_id)
                    attr_pairs = []
                    for attr in series_attrs:
                        attr_pairs.append((attr.attribute_type_id, attr.attribute_value_id))

                    # Сортируем для создания уникального ключа
                    attr_pairs.sort(key=lambda x: (x[0], x[1]))

                    # Создаем ключ для кэша
                    attr_parts = [f"{attr_type}:{attr_value}" for attr_type, attr_value in attr_pairs]
                    cache_key = f"series_{metric_id}_{'_'.join(attr_parts)}"

                    # Проверяем, есть ли уже в кэше
                    if not self._series_cache.get(cache_key):
                        # Сохраняем в кэш
                        self._series_cache.set(cache_key, series)
                        total_loaded += 1

                offset += batch_size
                logger.info(f"📦 Загружено пачка: {min(offset, total_series)}/{total_series} серий")

            elapsed = asyncio.get_event_loop().time() - start_time
            logger.info(f"✅ Предзагружено {total_loaded} серий в кэш за {elapsed:.2f} сек")

        except Exception as e:
            logger.error(f"❌ Ошибка при предзагрузке серий: {e}")
            import traceback

            logger.error(traceback.format_exc())

    async def preload_periods_for_metric(self, metric_id: int, batch_size: int = 1000):
        """Предзагружает периоды для конкретной метрики с пагинацией"""

        logger.info(f"🔄 Предзагрузка периодов для метрики ID: {metric_id}...")
        start_time = asyncio.get_event_loop().time()
        cache_count = 0
        total_periods = 0

        try:
            # Сначала получаем общее количество серий для метрики
            series_count_stmt = select(func.count(MetricSeriesNewModel.id)).where(
                MetricSeriesNewModel.metric_id == metric_id
            )
            series_count_result = await self._execute_with_retry(series_count_stmt)
            total_series = series_count_result.scalar()

            if total_series == 0:
                logger.info(f"✅ Для метрики {metric_id} нет серий, пропускаем предзагрузку периодов")
                return

            logger.info(f"📊 Всего серий для загрузки периодов: {total_series}")

            # Загружаем серии пачками
            offset = 0
            while offset < total_series:
                # Проверяем лимит кэша
                if cache_count >= self._period_cache.maxsize:
                    logger.warning(
                        f"⚠️  Достигнут лимит кэша ({self._period_cache.maxsize} записей). Остановка предзагрузки."
                    )
                    break

                # Получаем пачку серий
                series_stmt = (
                    select(MetricSeriesNewModel.id)
                    .where(MetricSeriesNewModel.metric_id == metric_id)
                    .order_by(MetricSeriesNewModel.id)
                    .offset(offset)
                    .limit(batch_size)
                )

                series_result = await self._execute_with_retry(series_stmt)
                series_batch = series_result.all()

                if not series_batch:
                    break

                # Получаем ID серий из пачки
                series_ids = [s[0] for s in series_batch]

                # Получаем периоды для этих серий
                periods_stmt = select(MetricPeriodNewModel).where(MetricPeriodNewModel.series_id.in_(series_ids))
                periods_result = await self._execute_with_retry(periods_stmt)
                periods = periods_result.scalars().all()

                # Обрабатываем периоды
                for period in periods:
                    # Проверяем лимит кэша для каждой записи
                    if cache_count >= self._period_cache.maxsize:
                        break

                    # Создаем ключ для кэша периодов
                    cache_key = f"{period.series_id}_{period.period_type}_{period.period_year}"
                    if period.period_month:
                        cache_key += f"_{period.period_month}"
                    if period.period_quarter:
                        cache_key += f"_q{period.period_quarter}"
                    if period.period_week:
                        cache_key += f"_w{period.period_week}"

                    # Проверяем, есть ли уже в кэше
                    if not self._period_cache.get(cache_key):
                        # Сохраняем в кэш
                        self._period_cache.set(cache_key, period)
                        cache_count += 1

                    total_periods += 1

                offset += len(series_batch)
                logger.info(
                    f"📦 Обработано серий: {min(offset, total_series)}/{total_series}, "
                    f"периодов: {total_periods}, в кэш: {cache_count}"
                )

                # Пауза между пачками для разгрузки БД
                await asyncio.sleep(0.1)

            elapsed = asyncio.get_event_loop().time() - start_time
            logger.info(
                f"✅ Предзагружено {cache_count} периодов в кэш за {elapsed:.2f} сек "
                f"(всего обработано: {total_periods} периодов)"
            )

        except Exception as e:
            logger.error(f"❌ Ошибка при предзагрузке периодов: {e}")
            import traceback

            logger.error(traceback.format_exc())


async def bulk_insert_metric_data_vectorized(self, records: List[MetricDataNewModel]) -> int:
    """Векторизованная массовая вставка"""

    if not records:
        return 0

    try:
        # Создаем DataFrame из записей для векторизации
        import pandas as pd

        # Конвертируем в DataFrame
        df = pd.DataFrame(
            [
                {
                    "series_id": r.series_id,
                    "period_id": r.period_id,
                    "country_id": r.country_id,
                    "city_id": r.city_id if r.city_id else None,
                    "value_numeric": r.value_numeric,
                    "value_string": r.value_string,
                    "value_boolean": r.value_boolean,
                    "value_range_start": r.value_range_start,
                    "value_range_end": r.value_range_end,
                    "meta_data": r.meta_data,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                }
                for r in records
            ]
        )

        # Используем pd.io.sql для более быстрой вставки
        from sqlalchemy import create_engine
        import io

        # Создаем строковое представление DataFrame в CSV
        output = io.StringIO()
        df.to_csv(output, sep="\t", header=False, index=False)
        output.seek(0)

        # Используем COPY FROM для максимальной скорости
        raw_conn = await self.session.connection()
        cursor = await raw_conn.connection.cursor()

        # Создаем временную таблицу
        await cursor.execute(
            """
            CREATE TEMP TABLE temp_metric_data_copy (
                series_id INTEGER,
                period_id INTEGER,
                country_id INTEGER,
                city_id INTEGER,
                value_numeric NUMERIC,
                value_string VARCHAR,
                value_boolean BOOLEAN,
                value_range_start NUMERIC,
                value_range_end NUMERIC,
                meta_data JSONB,
                created_at TIMESTAMPTZ,
                updated_at TIMESTAMPTZ
            )
        """
        )

        # Копируем данные
        await cursor.copy_from(output, "temp_metric_data_copy", sep="\t", null="")

        # Вставляем избегая дубликатов
        await cursor.execute(
            """
            INSERT INTO metric_data_new 
            SELECT * FROM temp_metric_data_copy t
            WHERE NOT EXISTS (
                SELECT 1 FROM metric_data_new m
                WHERE m.series_id = t.series_id
                AND m.country_id = t.country_id
                AND m.period_id = t.period_id
                AND COALESCE(m.city_id, -1) = COALESCE(t.city_id, -1)
            )
        """
        )

        total_inserted = cursor.rowcount
        await cursor.execute("COMMIT")

        return total_inserted

    except Exception as e:
        await self.session.rollback()
        logger.error(f"Ошибка векторизованной вставки: {e}")
        raise
