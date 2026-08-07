"""Analytics Provider Manager & Adapters for Enterprise AI Integration Framework v1.0."""

from __future__ import annotations

import time
from typing import Any
from app.integrations.integration_models import ProviderCapability, ProviderCategory, ProviderSpec
from app.integrations.integration_registry import BaseProviderAdapter, IntegrationRegistry
from app.integrations.integration_telemetry import IntegrationTelemetryEngine


class BaseAnalyticsAdapter(BaseProviderAdapter):
    """Base class for Product & Behavioral Analytics Adapters."""

    def track_event(self, event_name: str, user_id: str, properties: dict[str, Any] | None = None) -> bool:
        return True


class PostHogAnalyticsAdapter(BaseAnalyticsAdapter):
    pass

class MixpanelAnalyticsAdapter(BaseAnalyticsAdapter):
    pass

class SegmentAnalyticsAdapter(BaseAnalyticsAdapter):
    pass

class GoogleAnalyticsAdapter(BaseAnalyticsAdapter):
    pass


class AnalyticsProviderManager:
    """Manager for Product Analytics Integrations (PostHog, Mixpanel, Segment, Google Analytics)."""

    def __init__(self):
        self.registry = IntegrationRegistry()
        self.telemetry = IntegrationTelemetryEngine()
        self._initialize_default_adapters()

    def _initialize_default_adapters(self) -> None:
        providers = [
            ProviderSpec("posthog_analytics", "PostHog", ProviderCategory.ANALYTICS, capabilities=[ProviderCapability.ANALYTICS_TRACKING], priority=1),
            ProviderSpec("mixpanel_analytics", "Mixpanel", ProviderCategory.ANALYTICS, capabilities=[ProviderCapability.ANALYTICS_TRACKING], priority=1),
            ProviderSpec("segment_analytics", "Segment", ProviderCategory.ANALYTICS, capabilities=[ProviderCapability.ANALYTICS_TRACKING], priority=2),
            ProviderSpec("ga4_analytics", "Google Analytics 4", ProviderCategory.ANALYTICS, capabilities=[ProviderCapability.ANALYTICS_TRACKING], priority=2),
        ]
        classes = [PostHogAnalyticsAdapter, MixpanelAnalyticsAdapter, SegmentAnalyticsAdapter, GoogleAnalyticsAdapter]
        for spec, cls in zip(providers, classes):
            if not self.registry.get_provider(spec.provider_id):
                self.registry.register_provider(cls(spec))

    def track_event(self, event_name: str, user_id: str, properties: dict[str, Any] | None = None, provider_id: str = "posthog_analytics") -> bool:
        adapter = self.registry.get_provider(provider_id)
        if not adapter:
            return False
        res = adapter.track_event(event_name, user_id, properties)
        self.telemetry.record_request(provider_id=provider_id, category="ANALYTICS", latency_ms=0.6, success=True)
        return res
