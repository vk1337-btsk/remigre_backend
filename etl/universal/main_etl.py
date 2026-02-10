# etl/universal/main.py
import argparse
import asyncio
import sys
from pathlib import Path

from etl.universal.configs.avg_monthly_sex_occupation import (
    create_avg_monthly_earnings_employees_sex_occupation_etl_config,
)
from etl.universal.service_etl import UniversalETL
from src.core.config.logging import setup_logger_to_file


logger = setup_logger_to_file()


# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


CONFIGS_ETL: dict = {
    "avg_monthly_sex_occupation": create_avg_monthly_earnings_employees_sex_occupation_etl_config,
}


async def run_etl(mode: str = "check"):
    """Запускает ETL процесс"""
    logger.info(f"Запуск ETL в режиме: {mode}")

    # Создаем конфигурацию
    config = create_avg_monthly_earnings_employees_sex_occupation_etl_config()

    # Отладочная информация о конфигурации
    logger.info(f"Имя конфигурации: {config.name}")
    logger.info(f"CSV файл: {config.csv_file}")
    logger.info(f"Колонка страны в конфиге: {config.metric.country_column}")
    logger.info(f"Колонка значения в конфиге: {config.metric.value_column}")
    logger.info(f"Размер маппинга стран: {len(config.country_mapping)}")
    logger.info(f"Атрибуты: {len(config.metric.attributes)}")

    async with UniversalETL(config) as etl:
        if mode == "check":
            logger.info("Начинаем проверку стран...")
            success = await etl.check_countries()
            if not success:
                logger.warning("⚠️  Внимание: проблемы с проверкой стран!")
            else:
                logger.info("✅ Проверка стран завершена")
        else:
            logger.info("Начинаем импорт данных...")
            await etl.import_data()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Универсальный ETL для загрузки метрик")
    parser.add_argument(
        "--mode",
        choices=["check", "load"],
        default="check",
        help="Режим работы: check (проверка стран) или load (импорт данных)",
    )

    args = parser.parse_args()

    asyncio.run(run_etl(mode=args.mode))

"""
# Проверка стран
python -m etl.universal.main_etl --mode check

# Загрузка данных
python -m etl.universal.main_etl --mode load
"""
