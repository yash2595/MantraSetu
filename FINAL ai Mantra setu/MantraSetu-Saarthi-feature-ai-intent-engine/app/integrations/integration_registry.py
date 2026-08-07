"""Centralized dynamic Provider Registry for Enterprise AI Integration Framework v1.0."""

from __future__ import annotations

import time
from threading import RLock
from typing import Any
from app.integrations.integration_models import (
    ProviderCapability,
    ProviderCategory,
    ProviderSpec,
)


class BaseProviderAdapter:
    """Abstract base class for all enterprise provider adapters."""

    def __init__(self, spec: ProviderSpec):
        self.spec = spec

    def get_spec(self) -> ProviderSpec:
        return self.spec

    def is_healthy(self) -> bool:
        """Default adapter health probe."""
        return True

    def ping(self) -> float:
        """Ping provider and return latency in ms."""
        start = time.perf_counter()
        _ = self.is_healthy()
        return (time.perf_counter() - start) * 1000.0


class IntegrationRegistry:
    """Thread-safe dynamic provider registry providing O(1) resolution (<2 ms target)."""

    _instance: IntegrationRegistry | None = None
    _lock: RLock = RLock()

    def __new__(cls) -> IntegrationRegistry:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._providers: dict[str, BaseProviderAdapter] = {}
                cls._instance._category_index: dict[ProviderCategory, list[str]] = {
                    cat: [] for cat in ProviderCategory
                }
            return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton registry for isolated testing."""
        with cls._lock:
            if cls._instance:
                cls._instance._providers.clear()
                for cat in ProviderCategory:
                    cls._instance._category_index[cat] = []

    def register_provider(self, adapter: BaseProviderAdapter) -> None:
        """Register a provider adapter dynamically."""
        with self._lock:
            spec = adapter.get_spec()
            self._providers[spec.provider_id] = adapter
            cat = spec.category
            if cat not in self._category_index:
                self._category_index[cat] = []
            if spec.provider_id not in self._category_index[cat]:
                self._category_index[cat].append(spec.provider_id)

    def unregister_provider(self, provider_id: str) -> bool:
        """Unregister a provider by ID."""
        with self._lock:
            adapter = self._providers.pop(provider_id, None)
            if adapter:
                cat = adapter.get_spec().category
                if cat in self._category_index and provider_id in self._category_index[cat]:
                    self._category_index[cat].remove(provider_id)
                return True
            return False

    def get_provider(self, provider_id: str) -> BaseProviderAdapter | None:
        """Retrieve a registered provider adapter (<2 ms)."""
        with self._lock:
            return self._providers.get(provider_id)

    def get_providers_by_category(self, category: ProviderCategory) -> list[BaseProviderAdapter]:
        """Retrieve all registered providers for a given category."""
        with self._lock:
            provider_ids = self._category_index.get(category, [])
            return [self._providers[pid] for pid in provider_ids if pid in self._providers]

    def discover_providers_by_capability(
        self, category: ProviderCategory, capability: ProviderCapability
    ) -> list[BaseProviderAdapter]:
        """Discover providers matching category and capability criteria."""
        with self._lock:
            adapters = self.get_providers_by_category(category)
            return [a for a in adapters if capability in a.get_spec().capabilities]

    def list_all_providers(self) -> list[dict[str, Any]]:
        """List summary of all registered providers."""
        with self._lock:
            return [a.get_spec().to_dict() for a in self._providers.values()]
