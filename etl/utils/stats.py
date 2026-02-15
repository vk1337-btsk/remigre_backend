# etl/utils/stats.py
"""
DTO для подсчёта статистики
"""
from datetime import datetime

from pydantic import BaseModel, Field, computed_field


class StatisticsETL(BaseModel):
    """Статистика ETL"""

    start_time: datetime = Field(default_factory=datetime.now, title="Время начала ETL")
    end_time: datetime = Field(default_factory=datetime.now, title="Время окончания ETL")

    total_rows: int = Field(default=0)
    parsed_rows: int = Field(default=0)
    resolved_rows: int = Field(default=0)
    inserted_rows: int = Field(default=0)

    batches_processed: int = Field(default=0)
    skipped_countries: int = Field(default=0)

    @computed_field
    @property
    def total_seconds(self) -> int:
        """Общее время выполнения ETL в секундах."""

        return int((self.end_time - self.start_time).total_seconds())


class StaticsticsCache(BaseModel):
    """Статистика КЭША"""

    pass
