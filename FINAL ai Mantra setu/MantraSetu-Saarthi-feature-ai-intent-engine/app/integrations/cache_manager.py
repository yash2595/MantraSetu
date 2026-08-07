"""Cache Manager & Adapters for Enterprise AI Integration Framework v1.0."""

from __future__ import annotations

import time
from typing import Any
from app.integrations.integration_models import ProviderCategory, ProviderSpec
from app.integrations.integration_registry import BaseProviderAdapter, IntegrationRegistry
from app.integrations.integration_telemetry import IntegrationTelemetryEngine


class BaseCacheAdapter(BaseProviderAdapter):
    """Base class for Cache Adapters."""

    def __init__(self, spec: ProviderSpec):
        super().__init__(spec)
        self._store: dict[str, tuple[Any, float | None]] = {}

    def get(self, key: str) -> Any | None:
        if key in self._store:
            val, exp = self._store[key]
            if exp is not None and time.time() > exp:
                del self._store[key]
                return None
            return val
        return None

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> bool:
        exp = (time.time() + ttl_seconds) if ttl_seconds else None
        self._store[key] = (value, exp)
        return True

    def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False


class RedisCacheAdapter(BaseCacheAdapter):
    pass

class MemoryCacheAdapter(BaseCacheAdapter):
    pass


class CacheManager:
    """Manager for Distributed & Local Caching (Redis, In-Memory)."""

    def __init__(self):
        self.registry = IntegrationRegistry()
        self.telemetry = IntegrationTelemetryEngine()
        self._initialize_default_adapters()

    def _initialize_default_adapters(self) -> None:
        providers = [
            ProviderSpec("redis_cache", "Redis Cache", ProviderCategory.CACHE, priority=1),
            ProviderSpec("memory_cache", "In-Memory LRU Cache", ProviderCategory.CACHE, priority=2),
        ]
        classes = [RedisCacheAdapter, MemoryCacheAdapter]
        for spec, cls in zip(providers, classes):
            if not self.registry.get_provider(spec.provider_id):
                self.registry.register_provider(cls(spec))

    def get(self, key: str, provider_id: str = "memory_cache") -> Any | None:
        adapter = self.registry.get_provider(provider_id)
        if adapter:
            return adapter.get(key)
        return None

    def set(self, key: str, value: Any, ttl_seconds: int | None = None, provider_id: str = "memory_cache") -> bool:
        adapter = self.registry.get_provider(provider_id)
        if adapter:
            return adapter.set(key, value, ttl_seconds)
        return False

    def delete(self, key: str, provider_id: str = "memory_cache") -> bool:
        adapter = self.registry.get_provider(provider_id)
        if adapter:
            return adapter.delete(key)
        return False
