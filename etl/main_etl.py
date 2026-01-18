"""
Просто основной метод для подгрузки данных метрик в БД
"""

import asyncio
from pathlib import Path
from typing import Literal, Optional

from etl.fill_avg_sex_ocu_cur import main as fill_avg_sex_ocu_cur
from etl.fill_labout_comes import main as fill_labout_comes
from etl.fill_labout_comes_by_sex import main as fill_labout_comes_by_sex
from etl.fill_monthly_average_temperatures import main as fill_monthly_average_temperatures
from src.core.config.logging import setup_logger_to_file


logger = setup_logger_to_file()


async def main(run: str, mode: Literal["import", "check"], script: Optional[str] = None, file: Optional[str] = None):
    """
    Универсальная точка входа.
    run="all" — запустить все скрипты
    run="one" — запустить один скрипт
    """

    if run == "all":
        """Запускает все скрипты по очереди."""
        for name, importer in SCRIPTS.items():
            logger.info(f"\n=== Запуск {name.upper()} ({mode}) ===")
            await importer(mode=mode)

    elif run == "one":
        if script not in SCRIPTS:
            raise ValueError(f"Неизвестный скрипт: {script}. Доступны: {list(SCRIPTS)}")

        importer = SCRIPTS[script]

        logger.info(f"\n=== Запуск {script.upper()} ({mode}) ===")
        await importer(mode=mode)
    else:
        raise ValueError("run must be 'all' or 'one'")


# ======================================================================================================================
SCRIPTS = {
    "fill_avg_sex_ocu_cur": fill_avg_sex_ocu_cur,
    "fill_labout_comes": fill_labout_comes,
    "fill_labout_comes_by_sex": fill_labout_comes_by_sex,
    "fill_monthly_average_temperatures": fill_monthly_average_temperatures,
}


if __name__ == "__main__":
    # raise RuntimeError("Этот скрипт нельзя запускать без причин!")
    asyncio.run(
        main(
            run="one",
            script="fill_monthly_average_temperatures",
            # mode="import",
            mode="check",
        )
    )
