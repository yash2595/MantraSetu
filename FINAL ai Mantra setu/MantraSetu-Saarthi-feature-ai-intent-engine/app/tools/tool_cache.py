"""Thread-Safe TTL Result Cache with Parameter Hashing v1.1."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.tools.tool_models import ToolResult

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ToolCache"
_COMPONENT_VERSION = "1.1.0"


class ToolCache:
    """Enterprise thread-safe TTL result cache using parameters MD5 hashing."""

    def __init__(self, default_ttl_seconds: float = 300.0) -> None:
        self._default_ttl = default_ttl_seconds
        # key -> (ToolResult, expire_timestamp)
        self._cache: dict[str, tuple[ToolResult, float]] = {}
        self._lock = RLock()
        self._hits_count = 0
        self._misses_count = 0

    def _hash_key(self, tool_name: str, parameters: dict[str, Any]) -> str:
        """Generate deterministic cache key hash from tool_name and parameter dictionary."""
        sorted_params = json.dumps(parameters or {}, sort_keys=True, default=str)
        raw_key = f"{tool_name}:{sorted_params}"
        return hashlib.md5(raw_key.encode("utf-8")).hexdigest()

    def get(self, tool_name: str, parameters: dict[str, Any]) -> ToolResult | None:
        """Retrieve cached result if valid and unexpired."""
        with self._lock:
            key = self._hash_key(tool_name, parameters)
            entry = self._cache.get(key)
            if not entry:
                self._misses_count += 1
                return None

            result, expire_ts = entry
            if time.time() > expire_ts:
                del self._cache[key]
                self._misses_count += 1
                return None

            self._hits_count += 1
            # Return cached copy marked as cached
            cached_result = ToolResult(
                invocation_id=result.invocation_id,
                tool_name=result.tool_name,
                status=result.status,
                data=dict(result.data),
                error_message=result.error_message,
                execution_time_ms=0.0,
                cached=True,
            )
            logger.debug("ToolCache HIT for tool '%s'", tool_name)
            return cached_result

    def set(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        result: ToolResult,
        ttl_seconds: float | None = None,
    ) -> None:
        """Store tool result in TTL cache."""
        with self._lock:
            key = self._hash_key(tool_name, parameters)
            ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
            expire_ts = time.time() + ttl
            self._cache[key] = (result, expire_ts)
            logger.debug("ToolCache STORED result for tool '%s' [TTL: %.1fs]", tool_name, ttl)

    def invalidate(self, tool_name: str | None = None) -> None:
        """Invalidate cached entries for a tool or clear entire cache."""
        with self._lock:
            if tool_name is None:
                self._cache.clear()
            else:
                # Invalidate matching keys
                keys_to_del = [k for k in self._cache.keys() if k.startswith(tool_name)]
                for k in keys_to_del:
                    del self._cache[k]

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose cache operational statistics."""
        with self._lock:
            total = self._hits_count + self._misses_count
            hit_rate = (self._hits_count / total) if total > 0 else 0.0
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "cached_entries_count": len(self._cache),
                "hits_count": self._hits_count,
                "misses_count": self._misses_count,
                "hit_rate": round(hit_rate, 4),
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
