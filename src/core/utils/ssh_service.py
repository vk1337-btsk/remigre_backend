import logging
from typing import Optional

from sshtunnel import SSHTunnelForwarder

from src.core.config import settings

logger = logging.getLogger(__name__)

_ssh_tunnel: Optional[SSHTunnelForwarder] = None


def start_ssh_tunnel(
    ssh_host: str,
    ssh_port: int,
    ssh_user: str,
    ssh_key_path: str,
    addresses: dict[str, tuple[str, int]],
) -> dict[str, int]:
    """Поднимает SSH-туннель для нескольких сервисов.

    Args:
        ssh_host (str): SSH хост
        ssh_port (int): SSH порт
        ssh_user (str): SSH юзер
        ssh_key_path (str): путь до SSH ключа
        addresses (dict[str, tuple[str, int]]): Словарь данными о сервисе и его хосте+порте, например:
        {
            "redis": ("redis-host", 6379),
            "mongo": ("mongo-host", 27017),
            "postgres": ("pg-host", 5432),
        }


    Returns:
        dict[str, int]: Вернёт словарь с сервисами и портами, например:
        {
            "redis": 54321,
            "mongo": 54322,
            "postgres": 54323,
        }
    """

    global _ssh_tunnel

    if _ssh_tunnel:
        logger.warning("[SSH]: Туннель уже запущен")
        return dict(zip(addresses.keys(), _ssh_tunnel.local_bind_ports))

    logger.info("[SSH]: Запуск SSH-туннеля...")

    remote_bind_addresses = list(addresses.values())
    local_bind_addresses = [("127.0.0.1", 0)] * len(addresses)

    _ssh_tunnel = SSHTunnelForwarder(
        (ssh_host, ssh_port),
        ssh_username=ssh_user,
        ssh_pkey=ssh_key_path,
        remote_bind_addresses=remote_bind_addresses,
        local_bind_addresses=local_bind_addresses,
    )

    _ssh_tunnel.start()

    ports_map = dict(zip(addresses.keys(), _ssh_tunnel.local_bind_ports))

    for name, (remote_host, remote_port) in addresses.items():
        logger.info(f"[SSH]: {name.upper()}: " f"127.0.0.1:{ports_map[name]} → {remote_host}:{remote_port}")

    return ports_map


def stop_ssh_tunnel():
    """Корректно закрывает SSH-туннель"""

    global _ssh_tunnel

    if not _ssh_tunnel:
        return

    try:
        logger.info("[SSH]: Остановка SSH-туннеля")
        _ssh_tunnel.stop()
    except Exception:
        logger.exception("[SSH]: Ошибка при остановке SSH-туннеля")
    finally:
        _ssh_tunnel = None
