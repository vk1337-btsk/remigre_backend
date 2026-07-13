# etl/services/db_service.py
"""
Асинхронный сервис для работы с БД
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, cast

from sqlalchemy import and_, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from etl.config.etl_config import (
    AttributeTypeDTO,
    AttributeValueDTO,
    MetricConfig,
    PeriodDataDTO,
)
from etl.utils.period_key import make_period_key
from src.core.config.logging import setup_logger_to_file
from src.core.models import (
    MetricAttributeTypeModel,
    MetricAttributeValueModel,
    MetricDataModel,
    MetricInfoModel,
    MetricPeriodModel,
    MetricSeriesAttribute,
    MetricSeriesModel,
)


logger = setup_logger_to_file()


class DBService:
    """Сервис для взаимодействия с БД"""

    def __init__(self, session: AsyncSession):
        """Инициализация параметров"""

        self.session = session

    #
    #
    #
    # ================= Метрика =================
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _execute(self, stmt):
        """Выполнить запрос с ретраями и автоматическим откатом при ошибке."""
        try:
            return await self.session.execute(stmt)
        except Exception as e:
            logger.error(f"Ошибка SQL: {e}")
            await self.session.rollback()
            raise

    #
    #
    #
    # ================= Метрика =================
    async def get_or_create_metric(self, metric_config: MetricConfig) -> MetricInfoModel:
        """Получить или создать метрику по slug."""

        stmt = select(MetricInfoModel).where(MetricInfoModel.slug == metric_config.slug)
        result = await self._execute(stmt)
        metric = result.scalar_one_or_none()

        if metric is None:
            logger.info(f"Метрика не найдена, создаем новую: {metric_config.name}")
            metric = MetricInfoModel(
                slug=metric_config.slug,
                name=metric_config.name,
                description=metric_config.description,
                category=metric_config.category,
                data_type=metric_config.data_type.value,
                source_name=metric_config.source_name,
                source_url=metric_config.source_url,
                meta_data=metric_config.meta_data,
                is_active=metric_config.is_active,
            )
            self.session.add(metric)
            await self.session.flush()
            logger.info(f"✅ Метрика создана: {metric.name} (ID: {metric.id})")
        else:
            metric = cast(MetricInfoModel, metric)
            logger.info(f"✅ Метрика найдена: {metric.name} (ID: {metric.id})")

        return metric

    #
    #
    #
    # ================= Серии =================
    async def find_series_by_hashes(self, metric_id: int, hashes: List[str]) -> Dict[str, int]:
        """Находит существующие серии по списку хэшей атрибутов.
        Возвращает словарь {hash: series_id}.
        """

        if not hashes:
            return {}
        stmt = select(MetricSeriesModel.attributes_hash, MetricSeriesModel.id).where(
            MetricSeriesModel.metric_id == metric_id, MetricSeriesModel.attributes_hash.in_(hashes)
        )
        result = await self._execute(stmt)
        return {row.attributes_hash: row.id for row in result}

    async def bulk_create_series(
        self, metric_id: int, series_to_create: List[Tuple[str, List[Tuple[int, int]]]]
    ) -> Dict[str, int]:
        if not series_to_create:
            return {}

        # 1. Создаём объекты серий с хэшем
        series_objects = []
        for h, attr_pairs in series_to_create:
            series_objects.append(
                MetricSeriesModel(
                    metric_id=metric_id,
                    attributes_hash=h,  # ← сохраняем хэш
                    is_active=True,
                    is_preset=False,
                )
            )
        self.session.add_all(series_objects)
        await self.session.flush()  # получаем ID

        # 2. Создаём связи атрибутов
        result = {}
        associations = []
        for (h, attr_pairs), series in zip(series_to_create, series_objects):
            result[h] = series.id
            for type_id, value_id in attr_pairs:
                associations.append(
                    MetricSeriesAttribute(
                        series_id=series.id,
                        attribute_type_id=type_id,
                        attribute_value_id=value_id,
                        is_primary=True,
                        is_filtered=None,
                        sort_order=0,
                    )
                )
        self.session.add_all(associations)
        await self.session.flush()
        return result

    #
    #
    #
    # ================= Периоды =================
    async def find_periods_by_data(self, periods_data: List[PeriodDataDTO]) -> Dict[str, int]:
        """Ищет существующие периоды по их атрибутам (без привязки к серии).
        Возвращает словарь {period_key: period_id}.
        """
        if not periods_data:
            return {}

        conditions = []
        for p in periods_data:
            conditions.append(
                and_(
                    MetricPeriodModel.period_type == p.period_type,
                    MetricPeriodModel.period_year == p.period_year,
                    MetricPeriodModel.period_month == p.period_month,
                    MetricPeriodModel.period_quarter == p.period_quarter,
                    MetricPeriodModel.period_week == p.period_week,
                )
            )
        stmt = select(MetricPeriodModel).where(or_(*conditions))
        result = await self._execute(stmt)
        found = {}
        for period in result.scalars().all():
            key = make_period_key(period)  # из модели
            found[key] = period.id
        return found

    async def bulk_create_periods(self, periods_to_create: List[PeriodDataDTO]) -> Dict[str, int]:
        """Создаёт периоды и возвращает словарь {period_key: id}."""

        if not periods_to_create:
            return {}

        objects = []
        for p in periods_to_create:
            period = MetricPeriodModel(
                period_type=p.period_type,
                period_year=p.period_year,
                period_month=p.period_month,
                period_quarter=p.period_quarter,
                period_week=p.period_week,
                date_start=p.date_start,
                date_end=p.date_end,
                collected_at=p.collected_at,
                meta_data=p.meta_data,
                is_active=True,
            )
            objects.append(period)

        self.session.add_all(objects)
        await self.session.flush()

        logger.debug(f"✅ Создано {len(objects)} периодов.")

        result = {}
        for period in objects:
            key = make_period_key(period)
            result[key] = period.id
        return result

    #
    #
    #
    # ================= Типы атрибутов =================
    async def bulk_create_attribute_types(self, types: List[AttributeTypeDTO]) -> Dict[str, int]:
        """Создаёт недостающие типы атрибутов.
        Возвращает словарь {code: id} для всех запрошенных кодов.
        """

        if not types:
            return {}

        codes = [t.code for t in types]
        stmt = select(MetricAttributeTypeModel).where(MetricAttributeTypeModel.code.in_(codes))
        result = await self._execute(stmt)
        existing = {obj.code: obj.id for obj in result.scalars().all()}

        to_create = []
        for t in types:
            if t.code not in existing:
                to_create.append(
                    MetricAttributeTypeModel(
                        code=t.code,
                        name=t.name,
                        value_type=t.value_type,
                        is_active=t.is_active,
                        is_filtered=t.is_filtered,
                        sort_order=t.sort_order,
                        meta_data=t.meta_data,
                    )
                )

        if to_create:
            self.session.add_all(to_create)
            await self.session.flush()
            for obj in to_create:
                existing[obj.code] = obj.id
                logger.debug(f"✅ Создан тип атрибута: {obj.code} (ID: {obj.id})")

        return existing

    #
    #
    #
    # ================= Значения атрибутов =================
    async def bulk_create_attribute_values(self, type_id: int, values: List[AttributeValueDTO]) -> Dict[str, int]:
        """Создаёт недостающие значения атрибутов для данного типа.
        Возвращает словарь {code: id}.
        """

        if not values:
            return {}

        codes = [v.code for v in values]
        stmt = select(MetricAttributeValueModel).where(
            MetricAttributeValueModel.attribute_type_id == type_id,
            MetricAttributeValueModel.code.in_(codes),
        )
        result = await self._execute(stmt)
        existing = {obj.code: obj.id for obj in result.scalars().all()}

        to_create = []
        for v in values:
            if v.code not in existing:
                to_create.append(
                    MetricAttributeValueModel(
                        attribute_type_id=type_id,
                        code=v.code,
                        name=v.name,
                        is_active=v.is_active,
                        is_filtered=v.is_filtered,
                        sort_order=v.sort_order,
                        meta_data=v.meta_data,
                    )
                )

        if to_create:
            self.session.add_all(to_create)
            await self.session.flush()
            for obj in to_create:
                existing[obj.code] = obj.id
                logger.debug(f"✅ Создано значение атрибута: {obj.code} (ID: {obj.id})")

        return existing

    #
    #
    #
    # =================  Данные метрик =================
    async def bulk_insert_metric_data(self, records: List[MetricDataModel]) -> int:
        """Быстрая массовая вставка данных с использованием временной таблицы."""

        logger.info(f"💾 Вставка {len(records)} записей...")
        if not records:
            return 0

        try:
            # Создаём временную таблицу
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

            # Подготавливаем значения для вставки
            values_list = []
            now = datetime.now(timezone.utc)
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
                        "created_at": now,
                        "updated_at": now,
                    }
                )

            # Вставляем во временную таблицу
            insert_temp = text(
                """
                INSERT INTO temp_metric_data 
                (series_id, period_id, country_id, city_id,
                 value_numeric, value_string, value_boolean,
                 value_range_start, value_range_end,
                 meta_data, created_at, updated_at)
                VALUES 
                (:series_id, :period_id, :country_id, :city_id,
                 :value_numeric, :value_string, :value_boolean,
                 :value_range_start, :value_range_end,
                 :meta_data, :created_at, :updated_at)
                """
            )
            await self.session.execute(insert_temp, values_list)

            # Вставляем из временной таблицы в основную, избегая дубликатов
            insert_stmt = text(
                """
                INSERT INTO metric_data 
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
                    FROM metric_data m
                    WHERE m.series_id = t.series_id
                      AND m.country_id = t.country_id
                      AND m.period_id = t.period_id
                      AND COALESCE(m.city_id, -1) = COALESCE(t.city_id, -1)
                )
                """
            )
            result = await self.session.execute(insert_stmt)
            total_inserted = result.rowcount  # type: ignore[attr-defined]

            await self.session.commit()
            logger.info(f"✅ Вставлено {total_inserted} уникальных записей из {len(records)}")
            return total_inserted

        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Ошибка bulk insert: {e}")
            raise

    #
    #
    #
    # =================  Добавил методы =================
    async def find_attribute_type_by_code(self, code: str) -> Optional[MetricAttributeTypeModel]:
        stmt = select(MetricAttributeTypeModel).where(MetricAttributeTypeModel.code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_attribute_value(self, type_id: int, code: str) -> Optional[MetricAttributeValueModel]:
        stmt = select(MetricAttributeValueModel).where(
            MetricAttributeValueModel.attribute_type_id == type_id,
            MetricAttributeValueModel.code == code,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_attribute_values_by_codes(self, type_id: int, codes: List[str]) -> Dict[str, int]:
        """Возвращает {code: id} для существующих значений."""
        stmt = select(MetricAttributeValueModel.code, MetricAttributeValueModel.id).where(
            MetricAttributeValueModel.attribute_type_id == type_id,
            MetricAttributeValueModel.code.in_(codes),
        )
        result = await self.session.execute(stmt)
        return {row.code: row.id for row in result}

    async def bulk_create_periods_and_return_ids(self, periods_to_create: List[PeriodDataDTO]) -> List[int]:
        """Создаёт периоды и возвращает список их ID в том же порядке, что и входной список."""

        if not periods_to_create:
            return []

        objects = []
        for p in periods_to_create:
            period = MetricPeriodModel(
                period_type=p.period_type,
                period_year=p.period_year,
                period_month=p.period_month,
                period_quarter=p.period_quarter,
                period_week=p.period_week,
                date_start=p.date_start,
                date_end=p.date_end,
                collected_at=p.collected_at,
                meta_data=p.meta_data,
                is_active=True,
            )
            objects.append(period)

        self.session.add_all(objects)
        await self.session.flush()
        return [obj.id for obj in objects]  # порядок сохранён
