"""Thread-Safe Infrastructure TTL Cache v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "RuntimeCache"
_COMPONENT_VERSION = "1.0.0"


class RuntimeCache:
    """Enterprise thread-safe TTL cache storing configuration settings and discovered service endpoints."""

    def __init__(self) -> None:
        # key -> (value, expire_timestamp)
        self._cache: dict[str, tuple[Any, float]] = {}
        self._lock = RLock()
        self._hits_count = 0
        self._misses_count = 0

    def get(self, key: str) -> Any | None:
        """Retrieve value from TTL cache."""
        with self._lock:
            if key in self._cache:
                val, exp = self._cache[key]
                if time.time() < exp:
                    self._hits_count += 1
                    return val
                else:
                    del self._cache[key]

            self._misses_count += 1
            return None

    def set(self, key: str, value: Any, ttl_seconds: float = 300.0) -> None:
        """Set value in TTL cache."""
        with self._lock:
            exp = time.time() + ttl_seconds
            self._cache[key] = (value, exp)

    def invalidate(self) -> None:
        """Purge all cached entries."""
        with self._lock:
            self._cache.clear()

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose cache operational statistics."""
        with self._lock:
            tot = self._hits_count + self._misses_count
            hit_ratio = round(self._hits_count / tot, 4) if tot > 0 else 1.0
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "entries_count": len(self._cache),
                "hits_count": self._hits_count,
                "misses_count": self._misses_count,
                "hit_ratio": hit_ratio,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            details=self.statistics(),
        )
