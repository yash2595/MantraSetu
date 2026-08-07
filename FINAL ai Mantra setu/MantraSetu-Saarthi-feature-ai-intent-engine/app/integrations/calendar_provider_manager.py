"""Calendar Provider Manager & Adapters for Enterprise AI Integration Framework v1.0."""

from __future__ import annotations

import time
from typing import Any
from app.integrations.integration_models import ProviderCategory, ProviderSpec
from app.integrations.integration_registry import BaseProviderAdapter, IntegrationRegistry
from app.integrations.integration_telemetry import IntegrationTelemetryEngine


class BaseCalendarAdapter(BaseProviderAdapter):
    """Base class for Calendar Adapters."""

    def create_event(self, title: str, start_iso: str, end_iso: str, attendees: list[str] | None = None) -> dict[str, Any]:
        evt_id = f"evt_{self.spec.name.lower()[:3]}_{int(time.time()*1000)}"
        return {
            "event_id": evt_id,
            "title": title,
            "start": start_iso,
            "end": end_iso,
            "attendees": attendees or [],
            "status": "CONFIRMED",
            "provider_id": self.spec.provider_id,
        }


class GoogleCalendarAdapter(BaseCalendarAdapter):
    pass

class OutlookCalendarAdapter(BaseCalendarAdapter):
    pass


class CalendarProviderManager:
    """Manager for Enterprise Calendar Systems (Google Calendar, Outlook Calendar)."""

    def __init__(self):
        self.registry = IntegrationRegistry()
        self.telemetry = IntegrationTelemetryEngine()
        self._initialize_default_adapters()

    def _initialize_default_adapters(self) -> None:
        providers = [
            ProviderSpec("google_calendar", "Google Calendar", ProviderCategory.CALENDAR, priority=1),
            ProviderSpec("outlook_calendar", "Outlook Calendar", ProviderCategory.CALENDAR, priority=1),
        ]
        classes = [GoogleCalendarAdapter, OutlookCalendarAdapter]
        for spec, cls in zip(providers, classes):
            if not self.registry.get_provider(spec.provider_id):
                self.registry.register_provider(cls(spec))

    def create_event(self, title: str, start_iso: str, end_iso: str, attendees: list[str] | None = None, provider_id: str = "google_calendar") -> dict[str, Any]:
        adapter = self.registry.get_provider(provider_id)
        if not adapter:
            raise RuntimeError(f"Calendar provider '{provider_id}' not found")
        res = adapter.create_event(title, start_iso, end_iso, attendees)
        self.telemetry.record_request(provider_id=provider_id, category="CALENDAR", latency_ms=1.1, success=True)
        return res
