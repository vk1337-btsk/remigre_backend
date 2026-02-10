import logging
from contextlib import contextmanager
from typing import Dict, Optional, Tuple

from sshtunnel import SSHTunnelForwarder


logger = logging.getLogger(__name__)


class SSHTunnelManager:
    """Менеджер SSH-туннеля для подключения к удаленным сервисам."""

    _instance: Optional["SSHTunnelManager"] = None
    _tunnel: Optional[SSHTunnelForwarder] = None
    _ports_map: Dict[str, int] = {}
    _reference_count: int = 0  # Счетчик ссылок для управления жизненным циклом

    def __new__(cls):
        """Реализация Singleton для управления одним туннелем во всем приложении."""

        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Инициализация менеджера туннеля.
        Singleton уже создан в __new__, избегаем повторной инициализации"""

        pass

    def start_tunnel(
        self, ssh_host: str, ssh_port: int, ssh_user: str, ssh_key_path: str, addresses: Dict[str, Tuple[str, int]]
    ) -> Dict[str, int]:
        """Запускает SSH-туннель для нескольких сервисов.

        Args:
            ssh_host (str): SSH хост
            ssh_port (int): SSH порт
            ssh_user (str): SSH пользователь
            ssh_key_path (str): путь до SSH ключа
            addresses (Dict[str, Tuple[str, int]]): Словарь с данными о сервисе и его хосте+порте, например:
            {
                "redis": ("redis-host", 6379),
                "mongo": ("mongo-host", 27017),
                "postgres": ("pg-host", 5432),
            }

        Returns:
            Dict[str, int]: Вернёт словарь с сервисами и портами, например:
            {
                "redis": 54321,
                "mongo": 54322,
                "postgres": 54323,
            }
        """

        self._reference_count += 1

        if self._tunnel and self._tunnel.is_active:
            logger.info("[SSH Manager]: Туннель уже запущен, используем существующий")
            return self._ports_map

        logger.info("[SSH Manager]: Запуск SSH-туннеля...")

        remote_bind_addresses = list(addresses.values())
        local_bind_addresses = [("127.0.0.1", 0)] * len(addresses)

        try:
            self._tunnel = SSHTunnelForwarder(
                (ssh_host, ssh_port),
                ssh_username=ssh_user,
                ssh_pkey=ssh_key_path,
                remote_bind_addresses=remote_bind_addresses,
                local_bind_addresses=local_bind_addresses,
            )

            self._tunnel.start()
            self._ports_map = dict(zip(addresses.keys(), self._tunnel.local_bind_ports))

            # Логируем информацию о проброшенных портах
            for name, (remote_host, remote_port) in addresses.items():
                logger.info(
                    f"[SSH Manager]: {name.upper()}: "
                    f"127.0.0.1:{self._ports_map[name]} → {remote_host}:{remote_port}"
                )

            logger.info(f"[SSH Manager]: Туннель успешно запущен. Ссылок: {self._reference_count}")
            return self._ports_map

        except Exception as e:
            self._reference_count -= 1
            logger.error(f"[SSH Manager]: Ошибка при запуске туннеля: {e}")
            raise

    def stop_tunnel(self):
        """Останавливает SSH-туннель, если больше нет активных ссылок."""

        if self._reference_count <= 0:
            return

        self._reference_count -= 1
        logger.info(f"[SSH Manager]: Остановка ссылки. Осталось ссылок: {self._reference_count}")

        if self._reference_count == 0 and self._tunnel:
            try:
                logger.info("[SSH Manager]: Останавливаем SSH-туннель")
                self._tunnel.stop()
                self._tunnel = None
                self._ports_map = {}
            except Exception as e:
                logger.error(f"[SSH Manager]: Ошибка при остановке туннеля: {e}")

    def get_ports(self) -> Dict[str, int]:
        """Возвращает текущую карту портов."""

        return self._ports_map.copy()

    def get_port(self, service_name: str) -> Optional[int]:
        """Возвращает локальный порт для указанного сервиса."""

        return self._ports_map.get(service_name)

    def is_active(self) -> bool:
        """Проверяет, активен ли туннель."""
        return self._tunnel is not None and self._tunnel.is_active

    def reset(self):
        """Сбрасывает состояние менеджера (для тестов)."""

        if self._tunnel and self._tunnel.is_active:
            self._tunnel.stop()
        self._tunnel = None
        self._ports_map = {}
        self._reference_count = 0

    @contextmanager
    def tunnel_context(
        self, ssh_host: str, ssh_port: int, ssh_user: str, ssh_key_path: str, addresses: Dict[str, Tuple[str, int]]
    ):
        """Контекстный менеджер для временного использования туннеля.

        Пример использования:
        ```
        with ssh_manager.tunnel_context(...) as ports:
            # Используем порты
            db_host = "127.0.0.1"
            db_port = ports["postgresql"]
        ```
        """

        try:
            ports = self.start_tunnel(ssh_host, ssh_port, ssh_user, ssh_key_path, addresses)
            yield ports
        finally:
            self.stop_tunnel()


# Глобальный экземпляр для удобного использования
ssh_manager = SSHTunnelManager()
