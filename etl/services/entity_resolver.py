# etl/services/entity_resolver.py
"""
Разрешение идентификаторов для пачки сырых записей.
Использует кэш и DBService, создаёт недостающие сущности массово.
"""
import asyncio
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple, cast

from sqlalchemy import select

from etl.config.config_schema import (
    AttributeTypeDTO,
    ETLConfig,
    ParsedAttributeDTO,
    PeriodDataDTO,
)
from etl.services import CacheService, DBService, RawRecord
from etl.utils.period_key import make_period_key
from src.core.config.logging import setup_logger_to_file
from src.ms_metric.models import (
    MetricAttributeTypeModel,
    MetricAttributeValueModel,
    MetricPeriodNewModel,
    MetricSeriesNewModel,
)


logger = setup_logger_to_file()


class EntityResolver:
    """Сервис получения ID для пачки сырых записей.

    Принимает список RawRecord и для каждой записи находит в кэше или БД
    или создаёт соответствующие записи в БД (страны, атрибуты, серии, периоды)
    и возвращает словари сопоставления "код → ID".

    Все операции выполнем массово (для всего батча), уменьшая количество запросов к БД.
    Результаты кэшируются в CacheService для ускорения последующих батчей.
    """

    def __init__(self, config: ETLConfig, cache: CacheService, db: DBService, metric_id: int):
        """Инициализация параметров"""

        self.config = config
        self.cache = cache
        self.db_service = db
        self.metric_id = metric_id

        # Блокировки для предотвращения гонок при создании сущностей
        self._type_locks: Dict[str, asyncio.Lock] = {}
        self._series_locks: Dict[str, asyncio.Lock] = {}
        self._period_locks: Dict[str, asyncio.Lock] = {}

    async def resolve_batch(
        self, raw_records: List[RawRecord]
    ) -> Tuple[Dict[str, List[int]], Dict[str, int], Dict[str, int]]:
        """Принимает список обработанных строк из одного батча записей (объектов RawRecord) и
        последовательно обрабатывает и разделяет их на :
        - страны (только поиск в кэше, без создания в БД) и возвращает ID;
        - атрибуты (типы + значения, с созданием недостающих);
        - серии (по комбинации атрибутов, с созданием недостающих);
        - периоды (с созданием недостающих).

        Args:
            raw_records: список сырых записей, полученных от DataParser.

        Returns:
            Кортеж из трёх словарей:
            - country_map: {название_страны: [country_id, ...]} # список ID стран, т.к. у нас маппинг может быть
            - series_map: {хэш_атрибутов: series_id}
            - period_map: {ключ_периода: period_id}

        Raises:
            - Если страна не найдена в кэше и нет подходящего маппинга,
              то вызывается ошибка и логгируется, т.к. страна всегда должна быть.
        """

        # Получаем страны
        country_names = {r["country_name"] for r in raw_records}
        country_map = await self._resolve_countries(country_names)

        # Получаем атрибуты
        all_attrs: Dict[Tuple[str, str], ParsedAttributeDTO] = {}  # { (type_code, value_code): ParsedAttributeDTO }
        for rec in raw_records:
            for attribute in rec["attributes"]:
                all_attrs[(attribute.type.code, attribute.value.code)] = attribute
        attr_map = await self._resolve_attributes(all_attrs)  # (type_code, value_code) -> (type_id, value_id)

        # Получаем серии
        series_hashes: Dict[str, List[Tuple[int, int]]] = {}  # { хэш атрибутов: (type_id, value_id) }
        for rec in raw_records:
            pairs = []
            for attribute in rec["attributes"]:
                type_id, value_id = attr_map[(attribute.type.code, attribute.value.code)]
                pairs.append((type_id, value_id))

            pairs.sort(key=lambda x: (x[0], x[1]))
            hash = self._hash_attr_pairs(pairs)
            series_hashes[hash] = pairs
            rec["series_hash"] = hash

        series_map = await self._resolve_series(series_hashes)

        # Получаем периоды
        period_dtos = {make_period_key(rec["period_data"]): rec["period_data"] for rec in raw_records}
        period_map = await self._resolve_periods(list(period_dtos.values()))

        return country_map, series_map, period_map

    @staticmethod
    def _hash_attr_pairs(pairs: List[Tuple[int, int]]) -> str:
        """Генерирует хэш из пар (type_id, value_id)"""

        return "_".join(f"{t}:{v}" for t, v in pairs)

    #
    #
    # ================= Страны =================
    async def _resolve_countries(self, country_names: Set[str]) -> Dict[str, List[int]]:
        """Получить список ID стран для каждого названия (может быть несколько из-за маппинга)."""

        result = {}
        for name in country_names:
            ids = []

            # Прямое совпадение в кэше
            country_id = await self.cache.get_country_id(name)
            if country_id is not None:
                ids.append(country_id)

            # Маппинг (может дать несколько ID)
            mapped_ids = await self._resolve_country_with_mapping(name)
            ids.extend(mapped_ids)

            # Убираем дубликаты (если прямое совпадение совпало с маппингом)
            ids = list(set(ids))

            if not ids:
                raise ValueError(f"❌ Страна не найдена и нет маппинга: {name}")

            result[name] = ids
        return result

    async def _resolve_country_with_mapping(self, country_name: str) -> List[int]:
        """Получает список ID стран из маппинга (все подходящие)."""

        ids = []
        if country_name in self.config.country_mapping:
            for mapped in self.config.country_mapping[country_name]:
                country_id = await self.cache.get_country_id(mapped)
                if country_id:
                    ids.append(country_id)
        return ids

    #
    #
    # ================= Атрибуты =================
    async def _resolve_attributes(
        self, attrs: Dict[Tuple[str, str], ParsedAttributeDTO]
    ) -> Dict[Tuple[str, str], Tuple[int, int]]:
        """Проверяет типы и значения атрибутов, создаёт недостающие в БДч.

        На входе: словарь {(type_code, value_code): ParsedAttributeDTO}
        На выходе: словарь {(type_code, value_code): (type_id, value_id)}

        Алгоритм:
        1. Извлекаем все уникальные типы атрибутов, получаем их ID (создаём недостающие).
        2. Группируем коды значений по type_id.
        3. Для каждого type_id:
           - ищем значения в кэше,
           - затем в БД,
           - создаём оставшиеся (под блокировкой).
        4. Формируем итоговый словарь.
        """

        # Обрабатываем типы атрибутов
        # Собираем уникальные DTO типов (по коду типа)
        type_dtos: Dict[str, AttributeTypeDTO] = {}

        for (tc, _), attr in attrs.items():
            type_dtos[tc] = attr.type

        # Получаем {code: type_id} + создаём недостающие
        type_map = await self._get_or_create_attribute_types(type_dtos)

        # Для быстрого обратного преобразования type_id -> code
        type_id_to_code = {v: k for k, v in type_map.items()}

        # Обрабатываем значения атрибутов
        # Группируем коды значений по type_id (убираем дубликаты внутри типа)
        values_by_type: Dict[int, Set[str]] = defaultdict(set)  # Группируем value_code по type_id

        for tc, vc in attrs.keys():
            type_id = type_map[tc]
            values_by_type[type_id].add(vc)

        # Результирующий словарь для всех комбинаций
        value_map: Dict[Tuple[str, str], Tuple[int, int]] = {}

        # Обрабатываем каждый тип отдельно
        for type_id, value_codes in values_by_type.items():

            # Локальный кэш для данного type_id: (type_id, value_code) -> value_id
            cached: Dict[Tuple[int, str], int] = {}
            need_fetch: List[str] = []  # коды, не найденные в кэше

            # Поиск в кэше
            for vc in value_codes:
                val_obj = await self.cache.get_attribute_value(type_id, vc)
                if val_obj:
                    cached[(type_id, vc)] = cast(int, val_obj.id)
                else:
                    need_fetch.append(vc)

            # Поиск в БД (массовый)
            if need_fetch:

                # Используем метод DBService, который возвращает {code: id} для существующих значений
                db_found = await self.db_service.find_attribute_values_by_codes(type_id, need_fetch)

                for vc, vid in db_found.items():
                    cached[(type_id, vc)] = vid
                    need_fetch.remove(vc)  # удаляем найденное из списка

                    # Кладём в кэш (создаём упрощённый объект, чтобы в следующий раз был хит)
                    await self.cache.set_attribute_value(
                        type_id,
                        MetricAttributeValueModel(
                            id=vid,
                            attribute_type_id=type_id,
                            code=vc,
                            name=vc,  # или можно взять из DTO, но для кэша достаточно
                            is_active=True,
                            is_filtered=False,
                            sort_order=0,
                            meta_data=None,
                        ),
                    )

            # Созданём недостающие значения
            if need_fetch:

                # Получаем код типа (нужен для извлечения исходного DTO значения)
                type_code = type_id_to_code[type_id]

                # Собираем DTO для значений, которые нужно создать
                values_to_create = [attrs[(type_code, vc)].value for vc in need_fetch]

                # Блокировка на уровне type_id, чтобы два батча не создавали одни и те же значения параллельно
                lock = self._get_lock(self._type_locks, f"value_{type_id}")
                async with lock:
                    # После получения блокировки повторно проверяем, не создал ли кто-то эти значения
                    # (можно было бы не проверять, но для надёжности оставлю)
                    # Метод bulk_create_attribute_values уже содержит проверку уникальности,
                    # но повторная проверка кэша не помешает
                    created = await self.db_service.bulk_create_attribute_values(type_id, values_to_create)

                for vc, vid in created.items():
                    cached[(type_id, vc)] = vid
                    # Сохраняем в кэш
                    await self.cache.set_attribute_value(
                        type_id,
                        MetricAttributeValueModel(
                            id=vid,
                            attribute_type_id=type_id,
                            code=vc,
                            name=vc,
                            is_active=True,
                            is_filtered=False,
                            sort_order=0,
                            meta_data=None,
                        ),
                    )

            # ---- 2d. Формирование результата для данного типа ----
            type_code = type_id_to_code[type_id]
            for (_, vc), vid in cached.items():
                value_map[(type_code, vc)] = (type_id, vid)

        return value_map

    async def _get_or_create_attribute_types(self, type_dtos: Dict[str, AttributeTypeDTO]) -> Dict[str, int]:
        """Возвращает {code: id}, создаёт недостающие типы из DTO

        Этапы:
        1. Для каждого кода типа проверяем кэш.
        2. Если нет в кэше — ищем в БД.
        3. Если нет в БД — добавляем в список на создание.
        4. Создаём недостающие типы массово (под блокировкой).
        """

        result: Dict[str, int] = {}
        need_create: List[AttributeTypeDTO] = []

        for code, dto in type_dtos.items():
            # Проверка кэша
            cached = await self.cache.get_attribute_type(code)
            if cached:
                result[code] = cast(int, cached.id)
                continue

            # Поиск в БД
            stmt = select(MetricAttributeTypeModel).where(MetricAttributeTypeModel.code == code)
            res = await self.db_service._execute(stmt)
            obj = res.scalar_one_or_none()
            if obj:
                result[code] = obj.id
                await self.cache.set_attribute_type(obj)
            else:
                need_create.append(dto)

        if need_create:

            # Блокировка на первом недостающем коде (гарантирует, что только один батч будет создавать типы)
            # Можно было бы использовать общую блокировку для всех типов, но для простоты так.
            first_code = need_create[0].code
            lock = self._get_lock(self._type_locks, first_code)

            async with lock:
                # Повторная проверка после блокировки — возможно, другой батч уже создал эти типы
                still_missing = []

                for dto in need_create:
                    if not await self.cache.get_attribute_type(dto.code):
                        still_missing.append(dto)

                if still_missing:
                    # Массовое создание типов в БД
                    created = await self.db_service.bulk_create_attribute_types(still_missing)
                    for dto in still_missing:
                        tid = created[dto.code]
                        result[dto.code] = tid
                        # Сохраняем в кэш
                        obj = MetricAttributeTypeModel(
                            id=tid,
                            code=dto.code,
                            name=dto.name,
                            value_type=dto.value_type,
                            is_active=dto.is_active,
                            is_filtered=dto.is_filtered,
                            sort_order=dto.sort_order,
                            meta_data=dto.meta_data,
                        )
                        await self.cache.set_attribute_type(obj)

        return result

    #
    #
    # ================= Серии =================
    async def _resolve_series(self, hash_to_pairs: Dict[str, List[Tuple[int, int]]]) -> Dict[str, int]:
        """Вход: {hash: [(type_id, value_id), ...]} -> Выход: {hash: series_id}.

        Этапы:
        1. Проверяем кэш.
        2. Для отсутствующих в кэше — ищем в БД по хэшам.
        3. Создаём недостающие серии (под блокировкой).
        """

        result = {}
        missing_hashes = []

        # Проверяем кэш
        for h in hash_to_pairs:
            cached = await self.cache.get_series(self.metric_id, h)
            if cached:
                result[h] = cached.id
            else:
                missing_hashes.append(h)

        # Ищем в БД
        if missing_hashes:
            found = await self.db_service.find_series_by_hashes(self.metric_id, missing_hashes)
            for h, sid in found.items():
                result[h] = sid
                series_obj = MetricSeriesNewModel(
                    id=sid,
                    metric_id=self.metric_id,
                    attributes_hash=h,
                    is_active=True,
                    is_preset=False,
                )
                await self.cache.set_series(self.metric_id, h, series_obj)
                missing_hashes.remove(h)  # удаляем найденный хэш из списка

        # Создаём недостающие
        if missing_hashes:

            # Блокировка на первом недостающем хэше
            first_hash = missing_hashes[0]
            lock = self._get_lock(self._series_locks, first_hash)

            async with lock:

                # Повторная проверка после блокировки
                still_missing = []

                for h in missing_hashes:
                    if not await self.cache.get_series(self.metric_id, h):
                        still_missing.append(h)

                if still_missing:
                    # Подготавливаем данные для создания: (хэш, список пар)
                    to_create = [(h, hash_to_pairs[h]) for h in still_missing]
                    created = await self.db_service.bulk_create_series(self.metric_id, to_create)
                    for h, sid in created.items():
                        result[h] = sid
                        series_obj = MetricSeriesNewModel(
                            id=sid,
                            metric_id=self.metric_id,
                            attributes_hash=h,
                            is_active=True,
                            is_preset=False,
                        )
                        await self.cache.set_series(self.metric_id, h, series_obj)

        return result

    #
    #
    # ================= Периоды =================
    async def _resolve_periods(self, period_dtos: List[PeriodDataDTO]) -> Dict[str, int]:
        """Вход: список PeriodDataDTO -> Выход: {period_key: period_id}
        Разрешает периоды, используя единый ключ make_period_key.

        Использует единую функцию make_period_key для генерации ключа.
        Этапы:
        1. Проверяем кэш.
        2. Для отсутствующих — ищем в БД по данным периода.
        3. Создаём недостающие периоды (под блокировкой).
        """

        result = {}
        # Словарь ключ -> DTO (для быстрого доступа)
        key_to_dto = {make_period_key(p): p for p in period_dtos}

        # 1. Проверяем кэш
        need_db_lookup = []
        for key, p in key_to_dto.items():
            cached = await self.cache.get_period(key)
            if cached:
                result[key] = cached.id
            else:
                need_db_lookup.append(p)

        # 2. Ищем в БД
        if need_db_lookup:
            found = await self.db_service.find_periods_by_data(need_db_lookup)
            found_keys = set(found.keys())
            remaining = []
            for p in need_db_lookup:
                key = make_period_key(p)
                if key in found_keys:
                    pid = found[key]
                    result[key] = pid
                    period_obj = MetricPeriodNewModel(
                        id=pid,
                        period_type=p.period_type,
                        period_year=p.period_year,
                        period_month=p.period_month,
                        period_quarter=p.period_quarter,
                        period_week=p.period_week,
                    )
                    await self.cache.set_period(key, period_obj)
                else:
                    remaining.append(p)
            need_db_lookup = remaining

        # 3. Создаём оставшиеся
        if need_db_lookup:
            # Блокировка на основе первого ключа
            first_key = make_period_key(need_db_lookup[0])
            lock = self._get_lock(self._period_locks, first_key)
            async with lock:
                # Повторная проверка после блокировки
                still_missing = []
                for p in need_db_lookup:
                    key = make_period_key(p)
                    if not await self.cache.get_period(key):
                        still_missing.append(p)

                if still_missing:
                    # Создаём периоды и получаем ID в том же порядке
                    created_ids = await self.db_service.bulk_create_periods_and_return_ids(still_missing)
                    for dto, pid in zip(still_missing, created_ids):
                        key = make_period_key(dto)
                        result[key] = pid
                        # Кладём в кэш
                        period_obj = MetricPeriodNewModel(
                            id=pid,
                            period_type=dto.period_type,
                            period_year=dto.period_year,
                            period_month=dto.period_month,
                            period_quarter=dto.period_quarter,
                            period_week=dto.period_week,
                        )
                        await self.cache.set_period(key, period_obj)

        return result

    #
    #
    # ================= Вспомогательные методы для блокировок =================
    def _get_lock(self, lock_dict: Dict[str, asyncio.Lock], key: str) -> asyncio.Lock:
        """Возвращает асинхронную блокировку для указанного ключа (создаёт при необходимости)."""

        if key not in lock_dict:
            lock_dict[key] = asyncio.Lock()
        return lock_dict[key]
