# etl/services/file_reader.py
"""
FileReaderService для асинхронного чтения CSV файла с разбивкой на чанки.
"""

import asyncio
from pathlib import Path
from typing import AsyncGenerator, Set

import pandas as pd

from etl.config.config_schema import ETLConfig
from src.core.config.logging import setup_logger_to_file


logger = setup_logger_to_file()


class FileReaderService:
    """Сервис для асинхронного чтения файла"""

    def __init__(self, config: ETLConfig) -> None:
        """Инициализация параметров"""

        self.config = config
        self.file_path = Path(config.csv_file)
        self._encoding = config.csv_encoding
        self._delimiter = config.csv_delimiter

        if not self._validate_file():
            raise FileNotFoundError(f"Файл не найден: {self.config.csv_file}")

    async def get_total_rows(self) -> int:
        """Подсчитывает количестов строк в файле"""

        loop = asyncio.get_event_loop()

        def _count():
            with open(self.file_path, "r", encoding=self._encoding, errors="ignore") as file:
                return sum(1 for _ in file) - 1

        return await loop.run_in_executor(None, _count)

    async def read_chunks(self, chunk_size: int) -> AsyncGenerator[pd.DataFrame, None]:
        """Асинхронно читает CSV чанками, не блокируя event loop."""

        loop = asyncio.get_event_loop()
        gen = await loop.run_in_executor(None, self._chunk_generator, chunk_size)
        total = 0
        while True:
            chunk = await loop.run_in_executor(None, self._safe_next, gen)
            if chunk is None:
                break
            total += len(chunk)
            yield chunk
        self.total_rows = total

    async def get_unique_countries(self, country_column: str, chunk_size: int) -> Set[str]:
        """Возвращает список уникальных стран из файла"""

        countries = set()
        async for chunk in self.read_chunks(chunk_size):
            if country_column in chunk.columns:
                unique = chunk[country_column].dropna().astype(str).str.strip()
                unique = unique[unique != ""]
                countries.update(unique.tolist())

        return countries

    #
    #
    #
    # ================= Вспомогательные методы =================
    def _chunk_generator(self, chunk_size: int):
        """Создаёт генератор, читающий CSV чанками."""

        reader = pd.read_csv(
            self.file_path,
            sep=self._delimiter,
            encoding=self._encoding,
            dtype=str,
            chunksize=chunk_size,
            na_filter=False,
            keep_default_na=False,
            low_memory=False,
        )

        # Очистка BOM и NaN
        for chunk in reader:
            chunk.columns = chunk.columns.str.replace("\ufeff", "")
            chunk = chunk.fillna("")
            yield chunk

    @staticmethod
    def _safe_next(generator):
        """Безопасно получает следующий элемент из генератора. Возвращает None при StopIteration."""

        try:
            return next(generator)
        except StopIteration:
            return None

    def _validate_file(self) -> bool:
        """Проверяет существование файла"""

        return self.file_path.exists() and self.file_path.is_file()
