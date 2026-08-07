"""Lightweight static metadata cache for MantraSetu AgentOS.

Architecture Layer: Cached Static Metadata
Ownership: Static immutable route, workflow, and UI metadata ONLY.
          NEVER caches runtime session state, conversation memory, or live AI responses.
Thread Safety: RLock-protected with lazy TTL expiration and version-aware invalidation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Any

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ContextCache"
_COMPONENT_VERSION = "4.1"


@dataclass(frozen=True)
class _CacheEntry:
    """Immutable cache entry with version tag and optional TTL expiration timestamp."""

    value: Any
    version: str
    expires_at: str | None = None  # ISO 8601 timestamp; None = no expiry


class ContextCache:
    """Lightweight thread-safe cache storing ONLY static route, workflow, and UI metadata.

    Features:
      - Version-aware invalidation: entries are evicted on version mismatch
      - Optional TTL: entries with expires_at are lazily evicted on access
      - Cleanup support: expired entries can be evicted in bulk via cleanup()
      - Hit/miss telemetry: statistics() exposes hit ratio for monitoring

    CRITICAL RULE: Never caches runtime session state, conversation memory, or live AI responses.

    Public API (backward-compatible):
        get(), set(), invalidate(), invalidate_by_version(), statistics(), health()
    """

    def __init__(self, version: str = _COMPONENT_VERSION) -> None:
        # Internal store: key -> _CacheEntry
        self._cache: dict[str, _CacheEntry] = {}
        self._current_version = version
        # Diagnostic counters
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._sets = 0
        self._started_at = datetime.now(timezone.utc).isoformat()
        # RLock allows recursive public method calls without deadlock
        self._lock = RLock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_expired(entry: _CacheEntry) -> bool:
        """Check if a cache entry has exceeded its TTL. Lazy expiration on access."""
        if entry.expires_at is None:
            return False
        return datetime.now(timezone.utc).isoformat() > entry.expires_at

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str, expected_version: str | None = None) -> Any | None:
        """Retrieve a static metadata entry by key.

        Applies lazy expiration: entries exceeding TTL are evicted on access.
        Applies version check: entries with mismatched version are evicted on access.
        Complexity: O(1).

        Args:
            key: Cache entry key string.
            expected_version: If provided, entry must match this version string.

        Returns:
            The cached value, or None if missing, expired, or version-mismatched.
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None

            # Lazy TTL eviction
            if self._is_expired(entry):
                del self._cache[key]
                self._misses += 1
                self._evictions += 1
                logger.debug(
                    "Cache entry expired [operation=get, key=%s, metadata_version=%s]",
                    key,
                    entry.version,
                )
                return None

            # Version mismatch eviction
            target_ver = expected_version or self._current_version
            if entry.version != target_ver:
                del self._cache[key]
                self._misses += 1
                self._evictions += 1
                logger.debug(
                    "Cache version mismatch [operation=get, key=%s, cached_version=%s, expected_version=%s]",
                    key,
                    entry.version,
                    target_ver,
                )
                return None

            self._hits += 1
            return entry.value

    def set(
        self,
        key: str,
        value: Any,
        version: str | None = None,
        ttl_seconds: float | None = None,
    ) -> None:
        """Store a static metadata entry in the cache.

        Args:
            key: Cache entry key string.
            value: Immutable static metadata value to cache.
            version: Version tag string. Defaults to current cache version.
            ttl_seconds: Optional time-to-live in seconds. None = no expiry.
        """
        expires_at: str | None = None
        if ttl_seconds is not None:
            from datetime import timedelta
            expires_dt = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
            expires_at = expires_dt.isoformat()

        entry = _CacheEntry(
            value=value,
            version=version or self._current_version,
            expires_at=expires_at,
        )
        with self._lock:
            self._cache[key] = entry
            self._sets += 1

    def invalidate(self, key: str | None = None) -> None:
        """Invalidate a single cache entry or the entire cache.

        Args:
            key: If provided, evicts only that key. If None, evicts all entries.
        """
        with self._lock:
            if key is not None:
                evicted = self._cache.pop(key, None)
                if evicted is not None:
                    self._evictions += 1
                    logger.debug("Cache entry invalidated [operation=invalidate, key=%s]", key)
            else:
                count = len(self._cache)
                self._cache.clear()
                self._evictions += count
                logger.info("Cache fully invalidated [operation=invalidate, evicted_count=%d]", count)

    def invalidate_by_version(self, version: str) -> None:
        """Evict all cache entries matching a specific metadata version string.

        Complexity: O(n) — intentional and documented as a maintenance operation.
        """
        with self._lock:
            keys_to_remove = [k for k, e in self._cache.items() if e.version == version]
            for k in keys_to_remove:
                del self._cache[k]
            self._evictions += len(keys_to_remove)
            logger.info(
                "Cache invalidated by version [operation=invalidate_by_version, version=%s, evicted_count=%d]",
                version,
                len(keys_to_remove),
            )

    def cleanup(self) -> int:
        """Evict all expired cache entries. Useful for periodic maintenance.

        Complexity: O(n) — intentional maintenance operation.

        Returns:
            Count of evicted expired entries.
        """
        with self._lock:
            expired_keys = [k for k, e in self._cache.items() if self._is_expired(e)]
            for k in expired_keys:
                del self._cache[k]
            self._evictions += len(expired_keys)
            if expired_keys:
                logger.info(
                    "Cache cleanup completed [operation=cleanup, evicted_count=%d]",
                    len(expired_keys),
                )
            return len(expired_keys)

    def statistics(self) -> dict[str, Any]:
        """Return read-only enterprise diagnostics for ContextCache."""
        with self._lock:
            total = self._hits + self._misses
            hit_ratio = round(self._hits / total, 4) if total > 0 else 0.0
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cache_hits": self._hits,
                "cache_misses": self._misses,
                "total_requests": total,
                "hit_ratio": hit_ratio,
                "total_sets": self._sets,
                "total_evictions": self._evictions,
                "cached_keys_count": len(self._cache),
                "metadata_version": self._current_version,
            }

    def health(self) -> dict[str, Any]:
        """Return read-only health status for ContextCache."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "status": "HEALTHY",
                "cached_entries": len(self._cache),
                "metadata_version": self._current_version,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
