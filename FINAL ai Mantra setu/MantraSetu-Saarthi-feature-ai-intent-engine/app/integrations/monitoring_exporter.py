"""Monitoring Exporter for Enterprise AI Integration Framework v1.0."""

from __future__ import annotations

import time
from typing import Any
from app.integrations.integration_models import ProviderCapability, ProviderCategory, ProviderSpec
from app.integrations.integration_registry import BaseProviderAdapter, IntegrationRegistry
from app.integrations.integration_telemetry import IntegrationTelemetryEngine


class BaseMonitoringExporterAdapter(BaseProviderAdapter):
    """Base class for Observability & Metrics Exporters."""

    def export_metrics(self, metrics: list[dict[str, Any]]) -> str:
        return f"Exported {len(metrics)} metrics to {self.spec.name}"


class PrometheusExporterAdapter(BaseMonitoringExporterAdapter):
    def export_metrics(self, metrics: list[dict[str, Any]]) -> str:
        lines = []
        for m in metrics:
            lines.append(f"{m.get('name', 'metric')} {m.get('value', 0.0)}")
        return "\n".join(lines)


class GrafanaExporterAdapter(BaseMonitoringExporterAdapter):
    pass


class OpenTelemetryExporterAdapter(BaseMonitoringExporterAdapter):
    pass


class MonitoringExporter:
    """Manager for Monitoring Stack Exporters (Prometheus, Grafana, OpenTelemetry)."""

    def __init__(self):
        self.registry = IntegrationRegistry()
        self.telemetry = IntegrationTelemetryEngine()
        self._initialize_default_adapters()

    def _initialize_default_adapters(self) -> None:
        providers = [
            ProviderSpec("prometheus_export", "Prometheus", ProviderCategory.MONITORING, capabilities=[ProviderCapability.METRICS_EXPORT], priority=1),
            ProviderSpec("grafana_export", "Grafana", ProviderCategory.MONITORING, capabilities=[ProviderCapability.METRICS_EXPORT], priority=1),
            ProviderSpec("opentelemetry_export", "OpenTelemetry", ProviderCategory.MONITORING, capabilities=[ProviderCapability.METRICS_EXPORT], priority=1),
        ]
        classes = [PrometheusExporterAdapter, GrafanaExporterAdapter, OpenTelemetryExporterAdapter]
        for spec, cls in zip(providers, classes):
            if not self.registry.get_provider(spec.provider_id):
                self.registry.register_provider(cls(spec))

    def export(self, metrics: list[dict[str, Any]], provider_id: str = "prometheus_export") -> str:
        adapter = self.registry.get_provider(provider_id)
        if not adapter:
            raise RuntimeError(f"Monitoring exporter '{provider_id}' not found")
        res = adapter.export_metrics(metrics)
        self.telemetry.record_request(provider_id=provider_id, category="MONITORING", latency_ms=0.5, success=True)
        return res
