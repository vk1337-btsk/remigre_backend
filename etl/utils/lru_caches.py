# etl/utils/lru_cache.py
"""
Асинхронный потокобезопасный AsyncLRU-кэш
"""

import asyncio
from collections import OrderedDict
from typing import Any, Dict, Optional


class AsyncLRUCache:
    """LRU-кэш с защитой через asyncio.Lock."""

    def __init__(self, maxsize: int = 1000, name: str = "cache"):
        """Инициализация параметров"""

        self.maxsize = maxsize
        self.name = name
        self._cache: OrderedDict[Any, Any] = OrderedDict()
        self._lock = asyncio.Lock()
        self._stats: Dict[str, Any] = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "size": 0,
            "maxsize": maxsize,
            "name": name,
        }

    async def get_all_items(self) -> Dict[Any, Any]:
        """Возвращает копию всех элементов кэша."""

        async with self._lock:
            return dict(self._cache)

    async def get(self, key: Any) -> Optional[Any]:
        """Получить значение по ключу, переместить в конец (LRU)."""

        async with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._stats["hits"] += 1
                return self._cache[key]
            self._stats["misses"] += 1
            return None

    async def set(self, key: Any, value: Any) -> None:
        """Установить значение, при переполнении удалить самый старый."""

        async with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = value
            if len(self._cache) > self.maxsize:
                self._cache.popitem(last=False)
                self._stats["evictions"] += 1
            self._stats["size"] = len(self._cache)

    async def clear(self) -> None:

        async with self._lock:
            self._cache.clear()
            self._stats["hits"] = 0
            self._stats["misses"] = 0
            self._stats["evictions"] = 0
            self._stats["size"] = 0

    def size(self) -> int:
        """Текущий размер кэша (без блокировки, только для статистики)."""

        return len(self._cache)

    def stats(self) -> Dict[str, Any]:
        """Вернуть копию статистики с вычислением hit rate."""

        stats = self._stats.copy()
        total = stats["hits"] + stats["misses"]
        stats["hit_rate"] = (stats["hits"] / total * 100) if total > 0 else 0.0
        return stats
