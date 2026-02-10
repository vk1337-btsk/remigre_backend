# etl/universal/service_etl.py
"""
Универсальный ETL для загрузки данных метрик с поддержкой атрибутов-фильтров
"""

import asyncio
import csv
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Dict, List, cast

import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from etl.universal.config_schema import ETLConfig, GeographyLevelEnum
from etl.universal.service_db_etl import DB_ServiceUniversalETL
from etl.universal.session_manager import session_manager
from src.core.config.logging import setup_logger_to_file
from src.ms_metric.models import MetricDataNewModel


logger = setup_logger_to_file()


class UniversalETL:
    """Универсальный ETL процессор"""

    def __init__(self, config: ETLConfig):
        """Инициализация параметров"""

        self.config = config
        self.session: AsyncSession
        self.db_service: DB_ServiceUniversalETL
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_workers or 8)
        self.stats = {
            "total_rows": 0,
            "processed_rows": 0,
            "skipped_rows": 0,
            "errors": [],
            "start_time": None,
            "end_time": None,
        }

    async def __aenter__(self):
        """Контекстный менеджер для авто-создания сессии с предзагрузкой"""

        logger.info("Инициализация ETL сессии с предзагрузкой...")

        try:
            await session_manager.initialize()
            logger.info("Session manager инициализирован")

            self._session_context = session_manager.get_session()
            self.session = await self._session_context.__aenter__()
            logger.info(f"Сессия создана: {self.session}")

            self.db_service = DB_ServiceUniversalETL(self.session, config=self.config)
            logger.info("DB сервис создан")

            # Очищаем все кэши
            await self.db_service.clear_all_caches()

            # Предзагружаем данные в кэш перед началом обработки
            logger.info("\n🚀 Начинаем предзагрузку данных...")

            # Предзагружаем страны
            await self.db_service.preload_countries(column_name=self.config.country_column)

            # Получаем метрику для предзагрузки серий и периодов
            metric = await self.db_service.get_or_create_metric(self.config.metric)
            await self.session.commit()

            # Предзагружаем типы атрибутов
            if len(self.config.metric.attributes) > 0:
                await self.db_service.preload_attribute_types()
                await self.db_service.preload_attribute_values()

            # Предзагружаем серии и периоды для этой метрики
            await self.db_service.preload_series_for_metric(cast(int, metric.id))
            await self.db_service.preload_periods_for_metric(cast(int, metric.id))

            # Логируем начальную статистику кэшей
            await self.db_service.log_cache_stats()

            logger.info("✅ Предзагрузка завершена\n")

            return self
        except Exception as e:
            logger.error(f"Ошибка при инициализации ETL: {e}")
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Завершение контекстного менеджера с логированием статистики"""

        logger.info("Завершение ETL сессии...")

        # Логируем финальную статистику кэшей
        if hasattr(self, "db_service") and self.db_service:
            await self.db_service.log_cache_stats()

            # Дополнительная статистика
            logger.info("\n📊 ОБЩАЯ СТАТИСТИКА КЭШИРОВАНИЯ:")

            total_hits = 0
            total_misses = 0

            for cache_name in [
                "_country_cache",
                "_city_cache",
                "_metric_cache",
                "_series_cache",
                "_period_cache",
                "_attribute_type_cache",
                "_attribute_value_cache",
            ]:
                cache = getattr(self.db_service, cache_name, None)
                if cache and hasattr(cache, "stats"):
                    stats = cache.stats()
                    total_hits += stats["hits"]
                    total_misses += stats["misses"]

            total_requests = total_hits + total_misses
            if total_requests > 0:
                overall_hit_rate = (total_hits / total_requests) * 100
                logger.info(f"  Всего запросов к кэшам: {total_requests:,}")
                logger.info(f"  Попаданий: {total_hits:,} ({overall_hit_rate:.1f}%)")
                logger.info(f"  Промахов: {total_misses:,}")

        # Закрываем контекстный менеджер сессии
        if hasattr(self, "_session_context"):
            await self._session_context.__aexit__(exc_type, exc_val, exc_tb)

        # Закрываем менеджер сессий
        try:
            await session_manager.close()
            logger.info("Session manager закрыт")
        except Exception as e:
            logger.error(f"Ошибка при закрытии session manager: {e}")

    async def check_countries(self) -> bool:
        """Проверяет соответствие стран в CSV с БД и показывает обратную связь"""

        logger.info(f"\n{'='*60}")
        logger.info("ПРОВЕРКА СТРАН В CSV ФАЙЛЕ")
        logger.info(f"{'='*60}")

        # Предзагружаем страны для проверки
        if not self.db_service._countries_preloaded:
            await self.db_service.preload_countries(column_name=self.config.country_column)

        csv_path = Path(self.config.csv_file)
        if not csv_path.exists():
            logger.error(f"❌ Файл не найден: {self.config.csv_file}")
            return False

        logger.info(f"CSV файл: {csv_path}")
        logger.info(f"Кодировка: {self.config.csv_encoding}")
        logger.info(f"Разделитель: {repr(self.config.csv_delimiter)}")
        logger.info(f"Колонка для страны: '{self.config.metric.country_column}'")

        # 1. Получаем уникальные страны из CSV
        countries_in_csv = set()
        with open(csv_path, "r", encoding=self.config.csv_encoding) as f:
            reader = csv.DictReader(f, delimiter=self.config.csv_delimiter)

            # Удаляем BOM символы из имен колонок
            if reader.fieldnames:
                reader.fieldnames = [name.replace("\ufeff", "") for name in reader.fieldnames]
                logger.info(f"Очищенные заголовки: {reader.fieldnames}")

            if not reader.fieldnames:
                logger.error("❌ CSV не содержит заголовков (fieldnames=None)")
                return False

            # Проверяем, существует ли колонка страны
            if self.config.metric.country_column not in reader.fieldnames:
                logger.error(f"❌ Колонка '{self.config.metric.country_column}' не найдена в CSV!")
                logger.error(f"Доступные колонки: {reader.fieldnames}")
                return False

            row_count = 0
            for row in reader:
                row_count += 1
                country = row.get(self.config.metric.country_column, "").strip()
                if country:
                    countries_in_csv.add(country)

        logger.info(f"\nВсего строк прочитано: {row_count}")
        logger.info(f"Найдено {len(countries_in_csv)} уникальных стран в CSV")

        # Выводим первые 10 стран для проверки
        if countries_in_csv:
            logger.debug(f"Примеры стран из CSV (первые 10): {list(sorted(countries_in_csv))[:10]}")

        # 2. Получаем все страны из БД
        logger.info("\n🗺️  Получаем список всех стран из БД...")
        all_db_countries = await self.db_service._get_all_countries_from_db()

        if not all_db_countries:
            logger.error("❌ Не удалось получить список стран из БД")
            return False

        logger.info(f"Всего стран в БД: {len(all_db_countries)}")
        logger.info(f"Примеры стран из БД (первые 10): {list(sorted(all_db_countries.keys()))[:10]}")

        # 3. Проверяем каждую страну из CSV на наличие в БД
        countries_found = []
        countries_not_found = []
        mapping_used = []  # Для хранения использованных маппингов
        found_country_ids = set()  # ID стран, которые были найдены

        logger.info("\n🔍 Проверяем страны из CSV в базе данных...")

        for country_name in sorted(countries_in_csv):
            country_id = await self.db_service.get_country_id(
                country_name=country_name,
                country_mapping=self.config.country_mapping,
                column_name=self.config.country_column,
            )

            if country_id:
                countries_found.append(country_name)
                found_country_ids.add(country_id)

                # Проверяем, использовался ли маппинг
                if country_name in self.config.country_mapping:
                    mapping_used.append(country_name)
            else:
                countries_not_found.append(country_name)

        # 4. Определяем страны из БД, которых нет в CSV
        countries_in_db_not_in_csv = []
        for db_country_name, db_country_id in all_db_countries.items():
            if db_country_id not in found_country_ids:
                countries_in_db_not_in_csv.append((db_country_name, db_country_id))

        # 5. Выводим результаты CSV → БД
        logger.info(f"\n📊 СТАТИСТИКА ПРОВЕРКИ СТРАН (CSV → БД):")
        logger.info(f"   Всего уникальных стран в CSV: {len(countries_in_csv)}")
        logger.info(f"   Найдено в БД: {len(countries_found)}")
        logger.info(f"   Не найдено в БД: {len(countries_not_found)}")
        logger.info(f"   Процент соответствия: {(len(countries_found)/len(countries_in_csv))*100:.1f}%")

        # 6. Выводим результаты БД → CSV (информационно)
        logger.info(f"\n📊 СТАТИСТИКА ОБРАТНОЙ СВЯЗИ (БД → CSV):")
        logger.info(f"   Всего стран в БД: {len(all_db_countries)}")
        logger.info(f"   Использовано в CSV: {len(found_country_ids)}")
        logger.info(f"   Не использовано в CSV: {len(countries_in_db_not_in_csv)}")
        logger.info(f"   Процент охвата БД: {(len(found_country_ids)/len(all_db_countries))*100:.1f}%")

        if mapping_used:
            logger.info(f"\n🔄 Использован маппинг для {len(mapping_used)} стран:")
            for country_csv in mapping_used[:10]:
                db_names = self.config.country_mapping[country_csv]
                logger.info(f"   '{country_csv}' → {db_names}")
            if len(mapping_used) > 10:
                logger.info(f"   ... и еще {len(mapping_used) - 10} стран")

        # 7. Выводим страны из CSV, которых нет в БД
        if countries_not_found:
            logger.info(f"\n⚠️  СТРАНЫ В CSV, КОТОРЫХ НЕТ В БД ({len(countries_not_found)}):")
            for country in sorted(countries_not_found)[:30]:
                logger.info(f"   - {country}")
            if len(countries_not_found) > 30:
                logger.info(f"   ... и еще {len(countries_not_found) - 30} стран")

            # Создаем файл со списком стран для ручной проверки
            missing_file = Path("logs/missing_countries.txt")
            missing_file.parent.mkdir(exist_ok=True)
            with open(missing_file, "w", encoding="utf-8") as f:
                f.write("# Страны из CSV, которых нет в БД\n")
                f.write("# Добавьте их в country_mapping в конфигурации\n\n")
                for country in sorted(countries_not_found):
                    f.write(f"# {country}\n")
                    f.write(f"# '{country}': ['{country}'],\n\n")

            logger.info(f"\n📝 Список ненайденных стран сохранен в: {missing_file}")

        # 8. Выводим страны из БД, которых нет в CSV (информационно)
        if countries_in_db_not_in_csv:
            logger.info(f"\nℹ️  СТРАНЫ В БД, КОТОРЫХ НЕТ В CSV ({len(countries_in_db_not_in_csv)}):")
            for db_country_name, db_country_id in sorted(countries_in_db_not_in_csv, key=lambda x: x[0])[:50]:
                logger.info(f"   - {db_country_name} (ID: {db_country_id})")
            if len(countries_in_db_not_in_csv) > 50:
                logger.info(f"   ... и еще {len(countries_in_db_not_in_csv) - 50} стран")

            # Создаем файл со списком стран для информации
            unused_file = Path("logs/unused_countries.txt")
            unused_file.parent.mkdir(exist_ok=True)
            with open(unused_file, "w", encoding="utf-8") as f:
                f.write("# Страны в БД, которые не используются в CSV\n")
                f.write("# Информационный список - не требует действий\n\n")
                for db_country_name, db_country_id in sorted(countries_in_db_not_in_csv, key=lambda x: x[0]):
                    f.write(f"# {db_country_name} (ID: {db_country_id})\n")

            logger.info(f"\n📝 Список неиспользуемых стран сохранен в: {unused_file}")

        # 9. Выводим рекомендации
        if countries_not_found:
            logger.info("\n💡 РЕКОМЕНДАЦИИ:")
            logger.info("1. Проверьте правильность написания стран в CSV")
            logger.info("2. Проверьте, что страны в БД имеют правильные названия на английском (name_eng)")
            logger.info("3. Добавьте отсутствующие страны в маппинг (country_mapping) в конфигурации")
            logger.info("4. Проверьте файл missing_countries.txt для быстрого копирования")

            # ВАЖНО: Возвращаем True, так как это нормальная ситуация - не все страны могут быть в БД
            # В реальном ETL мы можем либо пропускать эти страны, либо использовать маппинг
            logger.info(f"\n⚠️  Внимание: {len(countries_not_found)} стран не найдены в БД")
            logger.info("Импорт будет продолжен для найденных стран.")
            return True  # Возвращаем True, чтобы ETL продолжал работу

        logger.info(f"\n✅ ВСЕ {len(countries_found)} СТРАН ИЗ CSV НАЙДЕНЫ В БД!")
        logger.info(f"✅ {len(found_country_ids)} ИЗ {len(all_db_countries)} СТРАН БД ИСПОЛЬЗУЮТСЯ В CSV")
        logger.info(f"\n{'='*60}")
        return True

    async def import_data(self):
        """Импортирует данные из CSV в БД"""

        self.stats["start_time"] = datetime.now()

        logger.info(f"\n{'='*60}")
        logger.info(f"ИМПОРТ ДАННЫХ: {self.config.name}")
        logger.info(f"Файл: {self.config.csv_file}")
        logger.info(f"{'='*60}")

        csv_path = Path(self.config.csv_file)
        if not csv_path.exists():
            logger.error(f"❌ Файл не найден: {self.config.csv_file}")
            return

        logger.info("📖 Чтение CSV через pandas...")
        df = pd.read_csv(
            csv_path,
            sep=self.config.csv_delimiter,
            encoding=self.config.csv_encoding,
            dtype=str,  # Все как строки для простоты
            na_filter=False,  # Не конвертировать пустые в NaN
            keep_default_na=False,
        )

        # Очищаем BOM из заголовков
        df.columns = df.columns.str.replace("\ufeff", "")
        logger.info(f"Очищенные заголовки: {list(df.columns)}")

        # Проверяем обязательные колонки
        missing_columns = self.config.required_columns - set(df.columns)
        if missing_columns:
            raise ValueError(f"Отсутствуют обязательные колонки: {', '.join(missing_columns)}")

        # Создаем/получаем метрику
        metric = await self.db_service.get_or_create_metric(self.config.metric)
        await self.session.commit()
        logger.info(f"✅ Метрика создана (ID: {metric.id})")

        batch: List[MetricDataNewModel] = []
        batch_counter = 0
        total_inserted = 0

        for row_idx, (_, row_series) in enumerate(df.iterrows(), 1):
            self.stats["total_rows"] += 1

            # Конвертируем pandas Series в dict
            row = row_series.to_dict()

            try:
                # Обрабатываем строку и добавляем в батч
                await self._process_row_to_batch(row, metric, batch, row_idx)

            except Exception as e:
                self.stats["skipped_rows"] += 1
                error_msg = f"Строка {row_idx}: {str(e)}"
                self.stats["errors"].append(error_msg)

                if not self.config.skip_invalid_rows:
                    raise
                else:
                    logger.warning(f"⚠️ Пропущена строка {row_idx}: {str(e)}")

            # ВСТАВЛЯЕМ БАТЧ bulk insert'ом
            if len(batch) >= self.config.batch_size:
                try:
                    # Bulk insert всего батча
                    inserted = await self.db_service.bulk_insert_metric_data(batch)
                    total_inserted += inserted
                    batch_counter += 1

                    logger.info(
                        f"✅ Батч #{batch_counter} сохранен: "
                        f"попытка {len(batch)} записей, "
                        f"вставлено {inserted} записей, "
                        f"всего вставлено: {total_inserted}"
                    )

                    # Очищаем батч
                    batch.clear()

                    if batch_counter % 10 == 0:
                        await self.db_service.log_cache_stats()

                except Exception as commit_error:
                    logger.error(f"❌ Ошибка bulk insert батча #{batch_counter}: {commit_error}")
                    await self.session.rollback()
                    raise

        # Вставка финального (неполного) батча
        if batch:  # Еще есть записи в батче
            try:
                inserted = await self.db_service.bulk_insert_metric_data(batch)
                total_inserted += inserted
                batch_counter += 1
                logger.info(
                    f"✅ Финальный батч #{batch_counter} сохранен: "
                    f"попытка {len(batch)} записей, "
                    f"вставлено {inserted} записей, "
                    f"всего вставлено: {total_inserted}"
                )
                batch.clear()  # Очищаем
            except Exception as commit_error:
                logger.error(f"❌ Ошибка финального bulk insert: {commit_error}")
                await self.session.rollback()
                raise

        # Обновляем статистику
        self.stats["processed_rows"] = total_inserted
        self.stats["duplicates_skipped"] = self.stats["total_rows"] - total_inserted - self.stats["skipped_rows"]

        # Выводим статистику
        self._print_statistics()

    def _print_statistics(self):
        """Выводит статистику импорта"""

        self.stats["end_time"] = datetime.now()
        duration = self.stats["end_time"] - self.stats["start_time"]

        db_stats = self.db_service.stats if self.db_service else {"duplicates_skipped": 0, "new_records": 0}

        logger.info(f"\n{'='*60}")
        logger.info("СТАТИСТИКА ИМПОРТА")
        logger.info(f"{'='*60}")
        logger.info(f"Время выполнения: {duration}")
        logger.info(f"Всего строк в CSV: {self.stats['total_rows']}")
        logger.info(f"Обработано строк: {self.stats['processed_rows']}")
        logger.info(f"Пропущено строк: {self.stats['skipped_rows']}")
        logger.info(f"Дубликатов пропущено: {db_stats['duplicates_skipped']}")
        logger.info(f"Новых записей создано: {db_stats['new_records']}")

        if self.stats["errors"]:
            logger.info(f"\nОшибки ({len(self.stats['errors'])}):")
            for error in self.stats["errors"][:10]:
                logger.info(f"  - {error}")
            if len(self.stats["errors"]) > 10:
                logger.info(f"  ... и еще {len(self.stats['errors']) - 10} ошибок")

        logger.info(f"\n✅ Импорт завершен!")

    async def _process_row_to_batch(self, row: Dict[str, str], metric, batch: List[MetricDataNewModel], row_idx: int):
        """Обрабатывает строку и добавляет запись в батч (без немедленной вставки)"""

        # row_start = time.time()

        # 1. Получаем страну (существующая логика)
        country_name = row.get(self.config.metric.country_column, "").strip()
        if not country_name:
            raise ValueError(f"Пустое название страны в строке {row_idx}")

        country_id = await self.db_service.get_country_id(
            country_name=country_name,
            country_mapping=self.config.country_mapping,
            column_name=self.config.country_column,
        )

        if not country_id:
            if self.config.validate_country_exists:
                raise ValueError(f"Страна не найдена в БД: {country_name}")
            return

        # 2. Получаем город (если нужно)
        city_id = None
        if self.config.geography_level == GeographyLevelEnum.CITY and self.config.metric.city_column:
            city_name = row.get(self.config.metric.city_column, "").strip()
            if city_name:
                city_id = await self.db_service.get_city_id(
                    city_name=city_name,
                    country_id=country_id,
                    city_mapping=self.config.city_mapping,
                )
                if not city_id:
                    logger.warning(f"Город не найден: {city_name}")

        # 3. Обрабатываем атрибуты
        attributes, complex_period_data = await self.db_service.process_attributes(
            row=row,
            attributes_config=self.config.metric.attributes,
        )

        # 4. Получаем или создаем серию
        series = await self.db_service.get_or_create_series(
            metric_id=metric.id,
            attributes=attributes,
            series_metadata=self.config.metric.series_metadata,
        )

        # 5. Получаем или создаем период
        period = await self.db_service.get_or_create_period(
            series_id=cast(int, series.id),
            period_config=self.config.metric.period,
            row=row,
            complex_period_data=complex_period_data,
        )

        # 6. Получаем значение метрики
        raw_value = row.get(self.config.metric.value_column, "").strip()
        if not raw_value:
            logger.debug(f"Пустое значение в строке {row_idx}, пропуск")
            return

        # Применяем трансформацию если есть
        if self.config.metric.value_transform:
            raw_value = self.config.metric.value_transform(raw_value)

        # 7. Создаем запись данных (но не вставляем!)
        data_record = await self.db_service.create_metric_data(
            series_id=cast(int, series.id),
            period_id=cast(int, period.id),
            country_id=country_id,
            city_id=city_id,
            value=raw_value,
            data_type=self.config.metric.data_type,
        )

        if data_record:
            batch.append(data_record)

        # logger.debug(f"Обработка строки {row_idx}: {time.time() - row_start} сек")

    async def import_data_parallel(self):
        """Параллельный импорт с использованием чанков"""
        self.stats["start_time"] = datetime.now()

        logger.info(f"\n{'='*60}")
        logger.info(f"ПАРАЛЛЕЛЬНЫЙ ИМПОРТ ДАННЫХ: {self.config.name}")
        logger.info(f"Файл: {self.config.csv_file}")
        logger.info(f"{'='*60}")

        csv_path = Path(self.config.csv_file)
        if not csv_path.exists():
            raise FileNotFoundError(f"Файл не найден: {self.config.csv_file}")

        # Создаем/получаем метрику
        metric = await self.db_service.get_or_create_metric(self.config.metric)
        await self.session.commit()

        # Определяем оптимальный размер чанка
        file_size = csv_path.stat().st_size
        chunk_size = self._calculate_optimal_chunk_size(file_size)

        logger.info(f"Размер файла: {file_size:,} байт")
        logger.info(f"Размер чанка: {chunk_size:,} строк")

        # Читаем файл чанками
        reader = pd.read_csv(
            csv_path,
            sep=self.config.csv_delimiter,
            encoding=self.config.csv_encoding,
            dtype=str,
            na_filter=False,
            chunksize=chunk_size,
            iterator=True,
        )

        # Обрабатываем чанки параллельно
        tasks = []
        chunk_counter = 0
        total_processed = 0

        for chunk_df in reader:
            chunk_counter += 1

            # Преобразуем чанк в список словарей для передачи в процессы
            chunk_data = chunk_df.to_dict("records")

            # Создаем задачу для обработки чанка
            task = asyncio.create_task(
                self._process_chunk_parallel(
                    chunk_data=chunk_data, metric=metric, chunk_number=chunk_counter, start_row=total_processed + 1
                )
            )
            tasks.append(task)

            total_processed += len(chunk_data)

            # Ограничиваем количество одновременно выполняемых задач
            if len(tasks) >= self.config.max_concurrent_chunks or 4:
                processed_count = await self._wait_for_tasks(tasks)
                total_processed += processed_count
                tasks = []

        # Обрабатываем оставшиеся задачи
        if tasks:
            processed_count = await self._wait_for_tasks(tasks)
            total_processed += processed_count

        self.stats["processed_rows"] = total_processed
        self._print_statistics()

    def _calculate_optimal_chunk_size(self, file_size: int) -> int:
        """Рассчитывает оптимальный размер чанка"""
        # Примерная эвристика: 10-100к строк на чанк в зависимости от размера файла
        if file_size < 10 * 1024 * 1024:  # < 10MB
            return 10000
        elif file_size < 100 * 1024 * 1024:  # < 100MB
            return 50000
        else:
            return 100000

    async def _wait_for_tasks(self, tasks: List[asyncio.Task]) -> int:
        """Ожидает завершения задач и возвращает общее количество обработанных строк"""
        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_processed = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Ошибка при обработке чанка: {result}")
                if not self.config.skip_invalid_rows:
                    raise result
            else:
                total_processed += result or 0

        return total_processed

    async def _process_chunk_parallel(
        self, chunk_data: List[Dict[str, str]], metric, chunk_number: int, start_row: int
    ) -> int:
        """Обрабатывает чанк данных в отдельном процессе"""
        # Используем ProcessPoolExecutor для CPU-bound операций
        with ProcessPoolExecutor(max_workers=1) as executor:
            loop = asyncio.get_event_loop()

            # Запускаем обработку в отдельном процессе
            processed_count = await loop.run_in_executor(
                executor, self._process_chunk_sync, chunk_data, metric.id, chunk_number, start_row
            )

            return processed_count

    def _process_chunk_sync(
        self, chunk_data: List[Dict[str, str]], metric_id: int, chunk_number: int, start_row: int
    ) -> int:
        """Синхронная обработка чанка (выполняется в отдельном процессе)"""
        # Этот метод выполняется в отдельном процессе,
        # поэтому нужно создать новую сессию для этого процесса
        import asyncio

        from etl.universal.session_manager import session_manager

        # Создаем новое событийное loop для этого процесса
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            return loop.run_until_complete(self._process_chunk_async(chunk_data, metric_id, chunk_number, start_row))
        finally:
            loop.close()

    async def _process_chunk_async(
        self, chunk_data: List[Dict[str, str]], metric_id: int, chunk_number: int, start_row: int
    ) -> int:
        """Асинхронная обработка чанка с локальной сессией"""
        # Создаем новую сессию для этого чанка
        async with session_manager.get_session() as local_session:
            # Создаем локальный сервис с кэшами
            local_db_service = DB_ServiceUniversalETL(local_session, self.config)

            # Копируем нужные кэши из основного сервиса
            await self._sync_caches_to_local(local_db_service)

            batch: List[MetricDataNewModel] = []
            processed_count = 0
            batch_counter = 0

            for i, row in enumerate(chunk_data, 1):
                row_idx = start_row + i - 1

                try:
                    # Используем локальный сервис для обработки
                    await self._process_single_row(
                        row=row, metric_id=metric_id, batch=batch, row_idx=row_idx, db_service=local_db_service
                    )

                except Exception as e:
                    self.stats["skipped_rows"] += 1
                    error_msg = f"Строка {row_idx}: {str(e)}"
                    self.stats["errors"].append(error_msg)

                    if not self.config.skip_invalid_rows:
                        raise

                # Вставляем батч
                if len(batch) >= self.config.batch_size:
                    try:
                        inserted = await local_db_service.bulk_insert_metric_data(batch)
                        processed_count += inserted
                        batch_counter += 1

                        logger.debug(f"Чанк {chunk_number}, батч {batch_counter}: " f"вставлено {inserted} записей")

                        batch.clear()

                    except Exception as e:
                        logger.error(f"Ошибка в чанке {chunk_number}, батче {batch_counter}: {e}")
                        raise

            # Вставляем финальный батч
            if batch:
                try:
                    inserted = await local_db_service.bulk_insert_metric_data(batch)
                    processed_count += inserted
                    batch.clear()
                except Exception as e:
                    logger.error(f"Ошибка финального батча чанка {chunk_number}: {e}")
                    raise

            await local_session.commit()
            return processed_count

    async def _process_single_row(
        self,
        row: Dict[str, str],
        metric_id: int,
        batch: List[MetricDataNewModel],
        row_idx: int,
        db_service: DB_ServiceUniversalETL,
    ):
        """Обрабатывает одну строку с использованием переданного сервиса"""
        # Логика аналогичная _process_row_to_batch, но с использованием переданного сервиса
        country_name = row.get(self.config.metric.country_column, "").strip()
        if not country_name:
            raise ValueError(f"Пустое название страны в строке {row_idx}")

        country_id = await db_service.get_country_id(
            country_name=country_name,
            country_mapping=self.config.country_mapping,
            column_name=self.config.country_column,
        )

        if not country_id:
            if self.config.validate_country_exists:
                raise ValueError(f"Страна не найдена в БД: {country_name}")
            return

        # Обработка города
        city_id = None
        if self.config.geography_level == GeographyLevelEnum.CITY and self.config.metric.city_column:
            city_name = row.get(self.config.metric.city_column, "").strip()
            if city_name:
                city_id = await db_service.get_city_id(
                    city_name=city_name,
                    country_id=country_id,
                    city_mapping=self.config.city_mapping,
                )

        # Обработка атрибутов
        attributes, complex_period_data = await db_service.process_attributes(
            row=row,
            attributes_config=self.config.metric.attributes,
        )

        # Получаем или создаем серию
        series = await db_service.get_or_create_series(
            metric_id=metric_id,
            attributes=attributes,
            series_metadata=self.config.metric.series_metadata,
        )

        # Получаем или создаем период
        period = await db_service.get_or_create_period(
            series_id=cast(int, series.id),
            period_config=self.config.metric.period,
            row=row,
            complex_period_data=complex_period_data,
        )

        # Получаем значение метрики
        raw_value = row.get(self.config.metric.value_column, "").strip()
        if not raw_value:
            return

        if self.config.metric.value_transform:
            raw_value = self.config.metric.value_transform(raw_value)

        # Создаем запись данных
        data_record = await db_service.create_metric_data(
            series_id=cast(int, series.id),
            period_id=cast(int, period.id),
            country_id=country_id,
            city_id=city_id,
            value=raw_value,
            data_type=self.config.metric.data_type,
        )

        if data_record:
            batch.append(data_record)

    async def _sync_caches_to_local(self, local_db_service: DB_ServiceUniversalETL):
        """Синхронизирует кэши из основного сервиса в локальный"""
        # Копируем кэши стран (только ключи, значения загрузим при необходимости)
        # В реальности лучше передавать сериализованные кэши
        pass
