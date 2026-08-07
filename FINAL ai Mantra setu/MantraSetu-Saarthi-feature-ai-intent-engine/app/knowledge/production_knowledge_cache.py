"""Production Knowledge Cache Manager for Enterprise RAG Layer Sprint 6C v1.1."""

from __future__ import annotations

import time
from threading import RLock
from typing import Any, Dict, Optional


class ProductionKnowledgeCache:
    """Thread-safe TTL cache manager for queries, embeddings, retrieval results, and citations."""

    def __init__(self, default_ttl_seconds: float = 300.0):
        self._lock = RLock()
        self._default_ttl = default_ttl_seconds
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._hits = 0
        self._misses = 0

    def get(self, cache_key: str) -> Optional[Any]:
        """Retrieve value from cache if not expired."""
        with self._lock:
            val_tuple = self._cache.get(cache_key)
            if not val_tuple:
                self._misses += 1
                return None

            val, exp = val_tuple
            if time.time() > exp:
                del self._cache[cache_key]
                self._misses += 1
                return None

            self._hits += 1
            return val

    def put(self, cache_key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        """Put value into cache with TTL expiration."""
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        with self._lock:
            self._cache[cache_key] = (value, time.time() + ttl)

    def invalidate(self, prefix: Optional[str] = None) -> int:
        """Invalidate cache entries by prefix or clear all."""
        with self._lock:
            if not prefix:
                cleared = len(self._cache)
                self._cache.clear()
                return cleared
            keys_to_del = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_del:
                del self._cache[k]
            return len(keys_to_del)

    def statistics(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            ratio = (self._hits / total * 100.0) if total > 0 else 0.0
            return {
                "active_cached_keys_count": len(self._cache),
                "total_cache_hits": self._hits,
                "total_cache_misses": self._misses,
                "hit_ratio_percentage": round(ratio, 2),
            }

    def health(self) -> Dict[str, Any]:
        return {"status": "HEALTHY", "ready": True}

    def metrics(self) -> Dict[str, Any]:
        return {"default_ttl_seconds": self._default_ttl, "invalidation_active": True}
