# etl/universal/lru_caches.py
"""
Сервис кэширования LRU
"""

from collections import OrderedDict
from typing import Any, Optional, Dict, Tuple
import asyncio


class LRUCache:
    """LRU кэш с ограничением размера и статистикой"""

    def __init__(self, maxsize: int = 10000, name: str = "unnamed"):
        """
        Args:
            maxsize: максимальный размер кэша
            name: имя кэша для логирования
        """
        self.cache: OrderedDict = OrderedDict()
        self.maxsize = maxsize
        self.name = name
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(self, key: Any) -> Optional[Any]:
        """Получить значение по ключу"""
        if key not in self.cache:
            self.misses += 1
            return None

        # Перемещаем в конец (самый недавно использованный)
        self.cache.move_to_end(key)
        self.hits += 1
        return self.cache[key]

    def set(self, key: Any, value: Any) -> None:
        """Установить значение по ключу"""
        if key in self.cache:
            # Обновляем существующее значение
            self.cache[key] = value
            self.cache.move_to_end(key)
        else:
            # Добавляем новое значение
            self.cache[key] = value

            # Если превысили размер, удаляем самый старый
            if len(self.cache) > self.maxsize:
                oldest_key, _ = self.cache.popitem(last=False)
                self.evictions += 1

    def delete(self, key: Any) -> bool:
        """Удалить значение по ключу"""
        if key in self.cache:
            del self.cache[key]
            return True
        return False

    def clear(self) -> None:
        """Очистить весь кэш"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def size(self) -> int:
        """Текущий размер кэша"""
        return len(self.cache)

    def stats(self) -> Dict[str, Any]:
        """Статистика использования кэша"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        return {
            "name": self.name,
            "size": self.size(),
            "maxsize": self.maxsize,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": f"{hit_rate:.1f}%",
            "fullness": f"{(self.size() / self.maxsize * 100):.1f}%" if self.maxsize > 0 else "0%",
        }

    def __contains__(self, key: Any) -> bool:
        return key in self.cache

    def __len__(self) -> int:
        return len(self.cache)


class AsyncLRUCache(LRUCache):
    """Асинхронная версия LRU кэша с блокировками для многопоточности"""

    def __init__(self, maxsize: int = 10000, name: str = "unnamed"):
        super().__init__(maxsize, name)
        self._lock = asyncio.Lock()

    async def get(self, key: Any) -> Optional[Any]:
        """Асинхронно получить значение по ключу"""
        async with self._lock:
            return super().get(key)

    async def set(self, key: Any, value: Any) -> None:
        """Асинхронно установить значение по ключу"""
        async with self._lock:
            super().set(key, value)

    async def delete(self, key: Any) -> bool:
        """Асинхронно удалить значение по ключу"""
        async with self._lock:
            return super().delete(key)

    async def clear(self) -> None:
        """Асинхронно очистить весь кэш"""
        async with self._lock:
            super().clear()

    async def stats(self) -> Dict[str, Any]:
        """Асинхронно получить статистику"""
        async with self._lock:
            return super().stats()
