"""System Telemetry for Enterprise AgentOS Integration Framework v1.0."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import RLock
from typing import Any
from app.system.system_models import _utc_now_iso


@dataclass
class SystemTelemetryMetric:
    """System telemetry metric record."""

    metric_name: str
    value: float
    tags: dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=_utc_now_iso)


class SystemTelemetry:
    """Global system telemetry aggregator recording framework invocation statistics."""

    _instance: SystemTelemetry | None = None
    _lock: RLock = RLock()

    def __new__(cls) -> SystemTelemetry:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._metrics: list[SystemTelemetryMetric] = []
            return cls._instance

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            if cls._instance:
                cls._instance._metrics.clear()

    def record_metric(self, name: str, value: float, tags: dict[str, str] | None = None) -> SystemTelemetryMetric:
        rec = SystemTelemetryMetric(metric_name=name, value=value, tags=tags or {})
        with self._lock:
            self._metrics.append(rec)
        return rec

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {"total_telemetry_metrics_recorded": len(self._metrics)}

    def health(self) -> dict[str, Any]:
        return {"status": "HEALTHY", "ready": True}

    def metrics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "telemetry_buffer_size": len(self._metrics),
                "export_latency_ms": 0.1,
            }
