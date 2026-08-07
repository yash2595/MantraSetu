"""Distributed Tracing & Span Lifecycle Manager v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.observability.observability_models import TraceContext, TraceSpan, TraceState
from app.observability.observability_telemetry import ObservabilityTelemetryEngine

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "TracingManager"
_COMPONENT_VERSION = "1.0.0"


class TracingManager:
    """Enterprise thread-safe manager handling distributed trace propagation and span lifecycles (<2ms target)."""

    def __init__(self, telemetry: ObservabilityTelemetryEngine | None = None) -> None:
        self._telemetry = telemetry or ObservabilityTelemetryEngine()
        self._spans: dict[str, TraceSpan] = {}
        self._lock = RLock()
        self._spans_created_count = 0

    def start_trace(self, name: str, baggage: dict[str, str] | None = None) -> TraceContext:
        """Initialize a new distributed trace context (<2ms target)."""
        with self._lock:
            context = TraceContext(baggage=dict(baggage or {}))
            self.start_span(context, name)
            return context

    def start_span(self, context: TraceContext, name: str) -> TraceSpan:
        """Start a new span within trace context."""
        start_ts = time.perf_counter()
        with self._lock:
            self._spans_created_count += 1
            span = TraceSpan(
                trace_id=context.trace_id,
                name=name,
                state=TraceState.ACTIVE,
            )
            self._spans[span.span_id] = span
            self._telemetry.record_trace_span()

            duration_ms = (time.perf_counter() - start_ts) * 1000
            logger.debug("TracingManager started span '%s' [%s] in %.2fms", name, span.span_id, duration_ms)
            return span

    def finish_span(self, span: TraceSpan, state: TraceState = TraceState.COMPLETED) -> None:
        """Complete a trace span and record duration."""
        with self._lock:
            if span.span_id in self._spans:
                s = self._spans[span.span_id]
                s.state = state
                # Calculate elapsed duration
                s.duration_ms = round((time.perf_counter() - time.perf_counter()) * 1000, 2)
                logger.debug("TracingManager finished span '%s'", s.span_id)

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose tracing manager operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "active_spans_count": sum(1 for s in self._spans.values() if s.state == TraceState.ACTIVE),
                "spans_created_count": self._spans_created_count,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            details=self.statistics(),
        )
