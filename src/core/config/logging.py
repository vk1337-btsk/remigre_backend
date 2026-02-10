import logging
import os
import sys
import warnings

from cryptography.utils import CryptographyDeprecationWarning
from src.core.config import settings

warnings.filterwarnings(
    "ignore",
    category=CryptographyDeprecationWarning,
)


def setup_logging(debug: bool = False):
    """Конфигурация логгирования"""

    level = logging.DEBUG if debug else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    # Понижаем уровень логирования
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("paramiko").setLevel(logging.WARNING)


def setup_logger_to_file(name: str = "import_logger") -> logging.Logger:
    """Создаёт логгер, который пишет в файл logs/logs.txt и выводит в консоль."""

    # Создаём папку logs, если нет
    os.makedirs("logs", exist_ok=True)

    # Файл логов
    log_filename = os.path.join("logs", "logs.txt")

    # Настройка формата
    log_format = "%(asctime)s | %(levelname)-8s | %(message)s"
    formatter = logging.Formatter(log_format)

    # Создаём логгер
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if settings.is_debug else logging.INFO)

    # Если хендлеры уже есть — не добавляем новые
    if logger.handlers:
        return logger

    # Консольный хендлер
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Файловый хендлер
    file_handler = logging.FileHandler(log_filename, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Понижаем уровень логирования
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").handlers.clear()

    return logger
