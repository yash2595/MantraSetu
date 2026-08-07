"""Dedicated Telemetry Aggregator Engine for AI Conversation Framework v1.0."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.conversation.conversation_models import RecoveryStrategyType

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ConversationTelemetryEngine"
_COMPONENT_VERSION = "1.0.0"


class ConversationTelemetryEngine:
    """Enterprise thread-safe telemetry aggregator tracking conversational latencies, accuracy, and recovery statistics."""

    def __init__(self) -> None:
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._lock = RLock()

        # Telemetry metrics
        self._turn_latencies: list[float] = []
        self._intent_confidences: list[float] = []
        self._slot_completion_rates: list[float] = []
        self._clarification_count = 0
        self._confirmation_count = 0
        self._recovery_counts: dict[str, int] = {}
        self._turns_processed_count = 0

    def record_turn_latency(self, latency_ms: float) -> None:
        """Record turn processing latency in milliseconds."""
        with self._lock:
            self._turns_processed_count += 1
            self._turn_latencies.append(latency_ms)
            if len(self._turn_latencies) > 1000:
                self._turn_latencies.pop(0)

    def record_intent_confidence(self, confidence: float) -> None:
        """Record intent classification confidence score."""
        with self._lock:
            self._intent_confidences.append(confidence)
            if len(self._intent_confidences) > 1000:
                self._intent_confidences.pop(0)

    def record_slot_completion(self, completion_rate: float) -> None:
        """Record session slot completion percentage."""
        with self._lock:
            self._slot_completion_rates.append(completion_rate)
            if len(self._slot_completion_rates) > 1000:
                self._slot_completion_rates.pop(0)

    def record_clarification(self) -> None:
        """Record clarification prompt event."""
        with self._lock:
            self._clarification_count += 1

    def record_confirmation(self) -> None:
        """Record confirmation prompt event."""
        with self._lock:
            self._confirmation_count += 1

    def record_recovery_event(self, strategy: RecoveryStrategyType | str) -> None:
        """Record recovery execution strategy event."""
        with self._lock:
            strat_name = str(strategy)
            self._recovery_counts[strat_name] = self._recovery_counts.get(strat_name, 0) + 1

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Compute telemetry operational statistics."""
        with self._lock:
            avg_latency = (sum(self._turn_latencies) / len(self._turn_latencies)) if self._turn_latencies else 0.0
            avg_confidence = (sum(self._intent_confidences) / len(self._intent_confidences)) if self._intent_confidences else 0.0
            avg_completion = (sum(self._slot_completion_rates) / len(self._slot_completion_rates)) if self._slot_completion_rates else 0.0

            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(time.perf_counter() - self._start_time, 2),
                "turns_processed_count": self._turns_processed_count,
                "average_turn_latency_ms": round(avg_latency, 2),
                "average_intent_confidence": round(avg_confidence, 4),
                "average_slot_completion_rate": round(avg_completion, 4),
                "clarification_count": self._clarification_count,
                "confirmation_count": self._confirmation_count,
                "recovery_counts": dict(self._recovery_counts),
            }

    def metrics(self) -> dict[str, Any]:
        """Expose operational metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report telemetry engine health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            details=self.statistics(),
        )
