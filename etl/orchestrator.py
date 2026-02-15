# etl/orchestrator.py
"""
Главный оркестратор ETL
"""
import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import List, Literal, cast

from sqlalchemy.ext.asyncio import AsyncSession

from etl.config.config_schema import ETLConfig
from etl.services import (
    CacheService,
    DataAssembler,
    DataParser,
    DBService,
    EntityResolver,
    FileReaderService,
    RawRecord,
)
from etl.utils.stats import StatisticsETL
from src.core.config.logging import setup_logger_to_file


logger = setup_logger_to_file()


class ETLOrchestrator:
    """ETL оркестратор"""

    def __init__(self, config: ETLConfig, session: AsyncSession):
        """Инициализация параметров"""

        self.config = config
        self.session = session

        # Сервисы
        self.cache_service = CacheService(config)
        self.db_service = DBService(session)
        self.file_reader = FileReaderService(config)
        self.parser = DataParser(config)
        self.assembler = DataAssembler(config)

        # Статистика
        self.statistics = StatisticsETL()

        self._stop_event = asyncio.Event()
        self._metric_id = None
        self._metric = None

    async def run(self, mode: Literal["check", "load"]):
        """Основной метод, запускающий ETL"""

        try:
            await self._initialize(mode)

            if mode == "check":
                await self.check_config()
            else:
                await self.import_data()

        finally:
            self.statistics.end_time = datetime.now()
            await self._log_statistics()

    def stop(self):
        """Остановка ETL"""

        self._stop_event.set()
        logger.info("🛑 Запрошена остановка ETL...")

    async def _initialize(self, mode: Literal["check", "load"]):
        """Инициализация основных действий"""

        logger.info("🔄 Инициализация ETL...")
        await self.cache_service.clear_all()

        # Подсчитываем кол-во строк в файле
        self.statistics.total_rows = await self.file_reader.get_total_rows()
        logger.info(f"📊 Всего строк в файле: {self.statistics.total_rows:,}")

        # Предзагружаем страны в кэш
        await self.cache_service.preload_countries(self.session, self.config.country_column)

        # TODO: вот тут нужно будет добавить условие для предзагрузки городов

        if mode == "load":
            # Получаем/создаём метрику по slug
            self._metric = await self.db_service.get_or_create_metric(self.config.metric)
            self._metric_id = cast(int, self._metric.id)
            await self.cache_service.set_metric(cast(str, self._metric.slug), self._metric)

            # Предзагружаем в кэш серии, периоды, типы и значения атрибутов
            await self.cache_service.preload_series(self.session, self._metric_id)
            await self.cache_service.preload_periods(self.session)
            await self.cache_service.preload_attribute_types(self.session)
            await self.cache_service.preload_attribute_values(self.session)

    #
    #
    # ================= Режим проверки =================
    async def check_config(self):
        """Проверка наличия стран из CSV в БД с учётом маппинга."""

        logger.info(f"{'='*20} РЕЖИМ ПРОВЕРКИ КОНФИГА")

        # Уникальные страны из файла
        logger.info("📖 Получение уникальных стран из CSV...")
        start_time = time.time()
        countries_in_csv = await self.file_reader.get_unique_countries(
            self.config.metric.country_column, self.config.chank_size
        )

        elapsed = time.time() - start_time
        logger.info(f"✅ Найдено {len(countries_in_csv)} уникальных стран за {elapsed:.2f} сек")

        # Получаем предзагруженные страны из кэша
        db_countries = await self.cache_service.get_all_countries()
        logger.debug(f"📊 Всего стран в БД: {len(db_countries)}")

        # Анализ
        countries_found = []  # Список найденных стран
        countries_not_found = []  # Список не найденных стран
        mapping_used = []  # Взято из маппинга

        # Сравниваем страны из файла со странами из БД
        for csv_country in sorted(countries_in_csv):
            # Проверяем полное совпадение: страна из файла -> страна из БД
            if csv_country in db_countries:
                countries_found.append(csv_country)
                continue

            # Проверяем совпадение по маппингу: страна из файла (маппинг) -> страна из БД
            if csv_country in self.config.country_mapping:
                mapped_names = self.config.country_mapping[csv_country]
                mapped_found = False
                for mapped_name in mapped_names:
                    if mapped_name in db_countries:
                        countries_found.append(csv_country)
                        mapping_used.append(f"'{csv_country}' -> '{mapped_name}'")
                        mapped_found = True
                        break

                    if mapped_found:
                        break

                if not mapped_found:
                    countries_not_found.append(csv_country)

            else:
                countries_not_found.append(csv_country)

        # Страны в БД, которых нет в CSV (с учётом маппинга)
        reverse_mapping = {}
        for csv_name, db_names in self.config.country_mapping.items():
            for db_name in db_names:
                reverse_mapping.setdefault(db_name, []).append(csv_name)

        # Получаю страны, которые есть в БД, но нет в файле (для информации)
        countries_in_db_not_in_csv = []
        for db_name, db_id in db_countries.items():
            used = False

            if db_name in countries_in_csv:
                used = True

            if not used:
                lower_db = db_name.lower()
                for csv_country in countries_in_csv:
                    if csv_country.lower() == lower_db:
                        used = True
                        break

            if not used and db_name in reverse_mapping:
                for csv_name in reverse_mapping[db_name]:
                    if csv_name in countries_in_csv:
                        used = True
                        break

            if not used:
                lower_db = db_name.lower()
                for mapped_db_name, csv_names in reverse_mapping.items():
                    if mapped_db_name.lower() == lower_db:
                        for csv_name in csv_names:
                            if csv_name in countries_in_csv:
                                used = True
                                break
                    if used:
                        break

            if not used:
                countries_in_db_not_in_csv.append((db_name, db_id))

        # Логирование результатов
        logger.info(f"{'='*20} 📊 РЕЗУЛЬТАТЫ:")
        logger.info(f"   Всего уникальных стран в CSV: {len(countries_in_csv)}")
        logger.info(f"   Найдено в БД: {len(countries_found)}")
        logger.info(f"   Не найдено в БД: {len(countries_not_found)}")

        # Если использовали маппинг
        if mapping_used:
            logger.info(f"\n🔄 Использован маппинг для {len(mapping_used)} стран:")
            for mapping in mapping_used[:5]:
                logger.info(f"   {mapping}")
            if len(mapping_used) > 5:
                logger.info(f"   ... и еще {len(mapping_used) - 5} маппингов")

        # Сохранение отчётов
        await self._save_country_reports(countries_not_found, countries_in_db_not_in_csv)

    #
    #
    # ================= Импорт данных =================
    async def import_data(self):
        """Импортирует данные из файла-источника в БД согласно конфигу"""

        logger.info(f"{'='*20} ИМПОРТ ДАННЫХ")

        raw_buffer: List[RawRecord] = []

        # Читаем файл чанками
        async for chunk_df in self.file_reader.read_chunks(self.config.chank_size):

            # Если передана остановка - останавливаем
            if self._stop_event.is_set():
                break

            # Парсинг чанка – запускаем в executor, чтобы не блокировать event loop
            loop = asyncio.get_event_loop()
            parsed = await loop.run_in_executor(None, self.parser.parse_chunk, chunk_df)
            raw_buffer.extend(parsed)
            self.statistics.parsed_rows += len(parsed)

            # Обрабатываем батчи (создаём и/или получаем ID объектов из БД и загружаем данные в БД )
            while len(raw_buffer) >= self.config.batch_size and not self._stop_event.is_set():
                batch = raw_buffer[: self.config.batch_size]
                raw_buffer = raw_buffer[self.config.batch_size :]
                await self._process_batch(batch)

        # Остаток
        if raw_buffer and not self._stop_event.is_set():
            await self._process_batch(raw_buffer)

    async def _process_batch(self, batch: List[RawRecord]):
        """Обработать один батч: разрешить сущности, собрать данные, вставить в БД."""

        logger.info(f"🔄 Обработка батча из {len(batch)} записей...")

        # Инициализируем сервис и обрабатываем батч (получаем ID всех сущностей из батча)
        resolver = EntityResolver(self.config, self.cache_service, self.db_service, cast(int, self._metric_id))
        country_map, series_map, period_map = await resolver.resolve_batch(batch)

        # Осуществляем сборку моделей
        records = self.assembler.assemble(batch, country_map, series_map, period_map)
        self.statistics.resolved_rows += len(records)

        # Добавляем в БД данные
        if records:
            inserted = await self.db_service.bulk_insert_metric_data(records)
            self.statistics.inserted_rows += inserted

        self.statistics.batches_processed += 1

        if self.statistics.batches_processed % 10 == 0:
            logger.info(
                f"📊 Обработано батчей: {self.statistics.batches_processed}, "
                f"вставлено записей: {self.statistics.inserted_rows:,}"
            )

    #
    #
    # ================= Статистика и отчёты =================
    async def _log_statistics(self):
        """Логгирует статистку ETL"""

        logger.info(f"{'='*20} 📊 СТАТИСТИКА ETL")

        logger.info(f"Общее время: {self.statistics.total_seconds:.2f} сек")
        logger.info(f"Всего строк: {self.statistics.total_rows:,}")
        logger.info(f"Распарсено строк: {self.statistics.parsed_rows:,}")
        logger.info(f"Успешно обработано (вставлено): {self.statistics.inserted_rows:,}")
        logger.info(f"Батчей обработано: {self.statistics.batches_processed}")

        if self.statistics.total_seconds > 0 and self.statistics.parsed_rows > 0:
            rows_per_second = self.statistics.parsed_rows / self.statistics.total_seconds
            logger.info(f"Скорость обработки: {rows_per_second:.1f} строк/сек")

        # Статистика кэшей
        cache_stats = self.cache_service.get_cache_stats()
        logger.info("\n📊 СТАТИСТИКА КЭШЕЙ:")
        for name, stats in cache_stats.items():
            hit_rate = stats.get("hit_rate", 0)
            size = stats.get("size", 0)
            maxsize = stats.get("maxsize", 1)
            fullness = (size / maxsize * 100) if maxsize > 0 else 0
            logger.info(
                f"{stats.get('name', name):25} | Hit rate: {hit_rate:5.1f}% | "
                f"Размер: {size:6}/{maxsize:6} ({fullness:5.1f}%) | Вытеснено: {stats.get('evictions', 0):6}"
            )
        logger.info("=" * 60)

    async def _save_country_reports(self, countries_not_found: list, countries_in_db_not_in_csv: list) -> None:
        """Сохраняет отчёт по проверке в отдельные файлы logs/missing_countries.txt и logs/unused_countries.txt"""

        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # ОСНОВНОЕ: отчёт по странам, которые есть в файле, но нет в БД (с учётом маппинга)
        if countries_not_found:
            missing_file = logs_dir / "missing_countries.txt"
            with open(missing_file, "w", encoding="utf-8") as f:
                f.write("# Страны из CSV, которых нет в БД\n")
                f.write("# Добавьте их в country_mapping в конфигурации\n\n")
                for country in sorted(countries_not_found):
                    if country in self.config.country_mapping:
                        mapping = self.config.country_mapping[country]
                        f.write(f"# Маппинг существует: {country} -> {mapping}\n")
                        f.write(f"# Проверьте правильность маппинга\n\n")
                    else:
                        f.write(f"# {country}\n")
                        f.write(f"'{country}': [],\n\n")
            logger.info(f"📝 missing_countries.txt создан: {missing_file}")

        # ДОПОЛНИТЕЛЬНО: отчёт по странам, которые есть в БД, но нет в файле
        if countries_in_db_not_in_csv:
            unused_file = logs_dir / "unused_countries.txt"
            with open(unused_file, "w", encoding="utf-8") as f:
                f.write("# Страны в БД, которые не используются в CSV\n")
                f.write("# Информационный список - не требует действий\n\n")
                for db_name, db_id in sorted(countries_in_db_not_in_csv, key=lambda x: x[0]):
                    f.write(f"# {db_name} (ID: {db_id})\n")
            logger.info(f"📝 unused_countries.txt создан: {unused_file}")

        if countries_not_found:
            logger.info(f"⚠️  ВНИМАНИЕ: {len(countries_not_found)} стран не найдены в БД")
            logger.info("   Проверьте файл missing_countries.txt для настройки маппинга")
            logger.info("   Импорт будет пропускать данные для этих стран")
        else:
            logger.info(f"\n✅ Отлично! Все страны из CSV найдены в БД")
