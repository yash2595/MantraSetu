"""Thread-Safe TTL Execution Cache for Plugins v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.plugins.plugin_models import PluginResult
from app.plugins.plugin_telemetry import PluginTelemetryEngine

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "PluginCache"
_COMPONENT_VERSION = "1.0.0"


class PluginCache:
    """Enterprise thread-safe TTL cache storing plugin execution results."""

    def __init__(self, telemetry: PluginTelemetryEngine | None = None) -> None:
        self._telemetry = telemetry or PluginTelemetryEngine()
        # request_id -> (PluginResult, expire_timestamp)
        self._cache: dict[str, tuple[PluginResult, float]] = {}
        self._lock = RLock()
        self._hits_count = 0
        self._misses_count = 0

    def get(self, request_id: str) -> PluginResult | None:
        """Get cached execution result if not expired."""
        with self._lock:
            if request_id in self._cache:
                res, exp = self._cache[request_id]
                if time.time() < exp:
                    self._hits_count += 1
                    self._telemetry.record_cache_hit()
                    logger.debug("PluginCache HIT for request '%s'", request_id)
                    return res
                else:
                    del self._cache[request_id]

            self._misses_count += 1
            return None

    def set(self, request_id: str, result: PluginResult, ttl_seconds: float = 300.0) -> None:
        """Cache execution result with TTL duration."""
        with self._lock:
            exp = time.time() + ttl_seconds
            self._cache[request_id] = (result, exp)

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
