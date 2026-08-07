"""Lightweight version-aware cache for immutable planning artifacts in MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "PlanningCache"
_COMPONENT_VERSION = "4.1"


@dataclass(frozen=True)
class _PlanningCacheEntry:
    """Immutable cache entry with version tag."""

    value: Any
    version: str
    created_at: str = datetime.now(timezone.utc).isoformat()


class PlanningCache:
    """Thread-safe cache storing static shortest paths and compiled navigation plans ONLY.
    
    CRITICAL RULE: Never caches runtime session state, conversation memory, or live user input.
    """

    def __init__(self, version: str = _COMPONENT_VERSION) -> None:
        self._cache: dict[str, _PlanningCacheEntry] = {}
        self._version = version
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._hits = 0
        self._misses = 0
        self._sets = 0

    def get(self, key: str) -> Any | None:
        """Retrieve cached planning artifact if version matches."""
        with self._lock:
            entry = self._cache.get(key)
            if entry and entry.version == self._version:
                self._hits += 1
                return entry.value
            self._misses += 1
            return None

    def set(self, key: str, value: Any) -> None:
        """Store immutable planning artifact in cache."""
        with self._lock:
            self._cache[key] = _PlanningCacheEntry(value=value, version=self._version)
            self._sets += 1

    def invalidate(self, key: str | None = None) -> None:
        """Evict a key or purge all entries."""
        with self._lock:
            if key:
                self._cache.pop(key, None)
            else:
                self._cache.clear()

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return diagnostic counters for PlanningCache."""
        with self._lock:
            total = self._hits + self._misses
            ratio = round((self._hits / total), 3) if total > 0 else 0.0
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "entries_count": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "hit_ratio": ratio,
                "sets": self._sets,
                "thread_safe": True,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose performance metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            message="PlanningCache operational.",
        )
