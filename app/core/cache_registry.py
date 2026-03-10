"""应用级共享缓存注册表。"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Callable, Dict, TypeVar


T = TypeVar("T")


@dataclass(slots=True)
class CacheRegistry:
    """集中管理命名缓存槽与状态。"""

    _caches: Dict[str, Any] = field(default_factory=dict)
    _statuses: Dict[str, str] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def get_dict_cache(self, name: str, initial: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """获取或创建 dict 缓存槽。"""

        with self._lock:
            if name not in self._caches:
                self._caches[name] = dict(initial or {})
            cache = self._caches[name]
        return cache

    def get(self, name: str, default: T | None = None) -> Any | T | None:
        """返回命名缓存槽当前值。"""

        with self._lock:
            return self._caches.get(name, default)

    def set(self, name: str, value: T) -> T:
        """写入命名缓存槽。"""

        with self._lock:
            self._caches[name] = value
        return value

    def get_or_create(self, name: str, factory: Callable[[], T]) -> T:
        """返回命名缓存槽，不存在则使用 factory 创建。"""

        with self._lock:
            cache = self._caches.get(name)
            if cache is None:
                cache = factory()
                self._caches[name] = cache
        return cache

    def clear(self, name: str) -> None:
        """清空指定缓存槽。"""

        with self._lock:
            cache = self._caches.get(name)
            if hasattr(cache, "clear"):
                cache.clear()
            else:
                self._caches.pop(name, None)
            self._statuses.pop(name, None)

    def reset_all(self) -> None:
        """清空全部缓存槽与状态。"""

        with self._lock:
            for cache in self._caches.values():
                if hasattr(cache, "clear"):
                    cache.clear()
            self._caches.clear()
            self._statuses.clear()

    def set_status(self, name: str, status: str) -> None:
        """记录命名缓存/资源状态。"""

        with self._lock:
            self._statuses[name] = status

    def get_status(self, name: str) -> str | None:
        """返回命名缓存/资源状态。"""

        with self._lock:
            return self._statuses.get(name)


_cache_registry = CacheRegistry()


def get_cache_registry() -> CacheRegistry:
    """返回共享缓存注册表。"""

    return _cache_registry


def reset_cache_registry() -> None:
    """清空共享缓存注册表。"""

    _cache_registry.reset_all()
