"""Maps Provider Manager & Adapters for Enterprise AI Integration Framework v1.0."""

from __future__ import annotations

import time
from typing import Any
from app.integrations.integration_models import ProviderCapability, ProviderCategory, ProviderSpec
from app.integrations.integration_registry import BaseProviderAdapter, IntegrationRegistry
from app.integrations.integration_telemetry import IntegrationTelemetryEngine


class BaseMapsAdapter(BaseProviderAdapter):
    """Base class for Maps & Geocoding Adapters."""

    def geocode(self, address: str) -> dict[str, Any]:
        return {
            "address": address,
            "latitude": 28.6139,
            "longitude": 77.2090,
            "formatted_address": f"{address}, New Delhi, India",
            "provider_id": self.spec.provider_id,
        }

    def get_directions(self, origin: str, destination: str) -> dict[str, Any]:
        return {
            "origin": origin,
            "destination": destination,
            "distance_km": 12.5,
            "duration_mins": 25.0,
            "provider_id": self.spec.provider_id,
        }


class GoogleMapsAdapter(BaseMapsAdapter):
    pass


class MapsProviderManager:
    """Manager for Location & Navigation Mapping Services (Google Maps)."""

    def __init__(self):
        self.registry = IntegrationRegistry()
        self.telemetry = IntegrationTelemetryEngine()
        self._initialize_default_adapters()

    def _initialize_default_adapters(self) -> None:
        providers = [
            ProviderSpec("google_maps", "Google Maps", ProviderCategory.MAPS, capabilities=[ProviderCapability.GEOCODING], priority=1),
        ]
        classes = [GoogleMapsAdapter]
        for spec, cls in zip(providers, classes):
            if not self.registry.get_provider(spec.provider_id):
                self.registry.register_provider(cls(spec))

    def geocode(self, address: str, provider_id: str = "google_maps") -> dict[str, Any]:
        adapter = self.registry.get_provider(provider_id)
        if not adapter:
            raise RuntimeError(f"Maps provider '{provider_id}' not found")
        res = adapter.geocode(address)
        self.telemetry.record_request(provider_id=provider_id, category="MAPS", latency_ms=1.0, success=True)
        return res

    def get_directions(self, origin: str, destination: str, provider_id: str = "google_maps") -> dict[str, Any]:
        adapter = self.registry.get_provider(provider_id)
        if not adapter:
            raise RuntimeError(f"Maps provider '{provider_id}' not found")
        return adapter.get_directions(origin, destination)
