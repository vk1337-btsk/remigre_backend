# etl/main.py
"""
Точка входа ETL
"""
import argparse
import asyncio
import signal
from typing import Callable, Literal

from etl.etl_configs import (
    create_avg_monthly_earnings_employees_sex_occupation_etl_config,
    create_lmoi_employment_rate_by_educational_attainment_etl_config,
    create_lmoi_employment_unemployment_and_participation_rates_by_sex_etl_config,
)
from etl.orchestrator import ETLOrchestrator
from etl.services.session_manager import session_manager
from src.core.config.logging import setup_logger_to_file


logger = setup_logger_to_file()


ETLConfigType = Literal[
    "avg_monthly_earnings",
    "employment_by_education",
    "employment_rates_by_sex",
]


CONFIG_FACTORY_MAP: dict[str, Callable] = {
    "avg_monthly_earnings": create_avg_monthly_earnings_employees_sex_occupation_etl_config,
    "employment_by_education": create_lmoi_employment_rate_by_educational_attainment_etl_config,
    "employment_rates_by_sex": create_lmoi_employment_unemployment_and_participation_rates_by_sex_etl_config,
}


async def run_etl(mode: Literal["check", "load"], config_type: ETLConfigType):

    logger.info(f"🚀 Запуск ETL | mode={mode} | config={config_type}")

    # Задаём конфиг
    try:
        config_factory = CONFIG_FACTORY_MAP[config_type]
    except KeyError:
        raise ValueError(f"Неизвестный тип конфига: {config_type}")
    await session_manager.initialize()

    config = config_factory()

    orchestrator = None
    stop_event = asyncio.Event()

    def _signal_handler(signum=None, frame=None):
        logger.warning("🛑 Получен сигнал остановки (Ctrl+C)")
        stop_event.set()
        if orchestrator:
            orchestrator.stop()

    loop = asyncio.get_running_loop()
    try:
        loop.add_signal_handler(signal.SIGINT, _signal_handler)
        loop.add_signal_handler(signal.SIGTERM, _signal_handler)
    except NotImplementedError:
        signal.signal(signal.SIGINT, _signal_handler)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _signal_handler)

    try:
        async with session_manager.get_session() as session:
            orchestrator = ETLOrchestrator(config, session)
            await orchestrator.run(mode)
    finally:
        await session_manager.close()


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--mode", choices=["check", "load"], default="check")

    parser.add_argument("--config", choices=list(CONFIG_FACTORY_MAP.keys()), required=True, help="Тип ETL конфига")

    args = parser.parse_args()

    try:
        asyncio.run(run_etl(mode=args.mode, config_type=args.config))

        print("\n✅ ETL процесс успешно завершен")
    except KeyboardInterrupt:
        print("\n🛑 Программа остановлена по Ctrl+C")
    except Exception as e:
        logger.error(f"\n❌ Ошибка: {e}")
        raise


if __name__ == "__main__":
    main()
