"""Search Provider Manager & Adapters for Enterprise AI Integration Framework v1.0."""

from __future__ import annotations

import time
from typing import Any
from app.integrations.integration_models import ProviderCategory, ProviderSpec
from app.integrations.integration_registry import BaseProviderAdapter, IntegrationRegistry
from app.integrations.integration_telemetry import IntegrationTelemetryEngine


class BaseSearchAdapter(BaseProviderAdapter):
    """Base class for Web Search Adapters."""

    def search(self, query: str, num_results: int = 5) -> list[dict[str, Any]]:
        return [
            {
                "title": f"Result {i+1} for '{query}' from {self.spec.name}",
                "snippet": f"Mock search snippet containing details about {query}.",
                "url": f"https://search.{self.spec.name.lower().replace(' ', '')}.com/result/{i+1}",
            }
            for i in range(num_results)
        ]


class GoogleSearchAdapter(BaseSearchAdapter):
    pass

class TavilySearchAdapter(BaseSearchAdapter):
    pass

class SerpAPISearchAdapter(BaseSearchAdapter):
    pass

class DuckDuckGoSearchAdapter(BaseSearchAdapter):
    pass


class SearchProviderManager:
    """Manager for Web Search Providers (Google Search, Tavily, SerpAPI, DuckDuckGo)."""

    def __init__(self):
        self.registry = IntegrationRegistry()
        self.telemetry = IntegrationTelemetryEngine()
        self._initialize_default_adapters()

    def _initialize_default_adapters(self) -> None:
        providers = [
            ProviderSpec("google_search", "Google Search", ProviderCategory.SEARCH, priority=1),
            ProviderSpec("tavily_search", "Tavily Search", ProviderCategory.SEARCH, priority=1),
            ProviderSpec("serpapi_search", "SerpAPI", ProviderCategory.SEARCH, priority=2),
            ProviderSpec("duckduckgo_search", "DuckDuckGo Search", ProviderCategory.SEARCH, priority=3),
        ]
        classes = [GoogleSearchAdapter, TavilySearchAdapter, SerpAPISearchAdapter, DuckDuckGoSearchAdapter]
        for spec, cls in zip(providers, classes):
            if not self.registry.get_provider(spec.provider_id):
                self.registry.register_provider(cls(spec))

    def search(self, query: str, num_results: int = 5, provider_id: str = "tavily_search") -> list[dict[str, Any]]:
        adapter = self.registry.get_provider(provider_id)
        if not adapter:
            adapters = self.registry.get_providers_by_category(ProviderCategory.SEARCH)
            adapter = adapters[0] if adapters else None
        if not adapter:
            return []
        res = adapter.search(query, num_results)
        self.telemetry.record_request(provider_id=adapter.get_spec().provider_id, category="SEARCH", latency_ms=1.5, success=True)
        return res
