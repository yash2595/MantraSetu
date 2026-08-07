"""AI Request Lifecycle Manager for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any
from uuid import uuid4

from app.core.models import ComponentHealth, SystemHealthStatus
from app.orchestrator.orchestrator_models import OrchestratorRequest, OrchestratorState, RequestDiagnostics
from app.orchestrator.orchestrator_state_machine import OrchestratorStateMachine

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "AIRequestLifecycleManager"
_COMPONENT_VERSION = "4.1"


class AIRequestLifecycleManager:
    """Manager coordinating request lifecycle, state machine transitions, correlation IDs, and cancellation."""

    def __init__(self, state_machine: OrchestratorStateMachine | None = None) -> None:
        self._state_machine = state_machine or OrchestratorStateMachine()
        self._diagnostics_store: dict[str, RequestDiagnostics] = {}
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._requests_managed_count = 0

    def start_request_lifecycle(
        self,
        request: OrchestratorRequest,
        parent_trace_id: str | None = None,
    ) -> RequestDiagnostics:
        """Start lifecycle tracking, generate trace/span IDs, and transition state to BUILDING_CONTEXT."""
        with self._lock:
            self._requests_managed_count += 1
            self._state_machine.init_request(request.request_id)

            diag = RequestDiagnostics(
                trace_id=f"tr_{uuid4().hex[:8]}",
                parent_trace_id=parent_trace_id,
                request_id=request.request_id,
                span_id=f"sp_{uuid4().hex[:8]}",
                timings={"start_time": time.perf_counter()},
            )
            self._diagnostics_store[request.request_id] = diag
            self._state_machine.transition(request.request_id, OrchestratorState.BUILDING_CONTEXT)
            return diag

    def transition_state(self, request_id: str, new_state: OrchestratorState) -> OrchestratorState:
        """Transition request state machine."""
        with self._lock:
            return self._state_machine.transition(request_id, new_state)

    def complete_request_lifecycle(self, request_id: str) -> RequestDiagnostics | None:
        """Complete lifecycle and finalize diagnostics."""
        with self._lock:
            if request_id in self._diagnostics_store:
                diag = self._diagnostics_store[request_id]
                start_t = diag.timings.get("start_time", time.perf_counter())
                elapsed_ms = (time.perf_counter() - start_t) * 1000.0
                diag.timings["total_latency_ms"] = round(elapsed_ms, 2)
                curr = self._state_machine.get_state(request_id)
                if curr not in (OrchestratorState.COMPLETED, OrchestratorState.FAILED, OrchestratorState.CANCELLED):
                    self._state_machine.transition(request_id, OrchestratorState.COMPLETED)
                return diag
            return None

    def cancel_request_lifecycle(self, request_id: str) -> None:
        """Mark lifecycle as CANCELLED if not already terminal."""
        with self._lock:
            if request_id in self._diagnostics_store:
                curr = self._state_machine.get_state(request_id)
                if curr not in (OrchestratorState.COMPLETED, OrchestratorState.FAILED, OrchestratorState.CANCELLED):
                    self._state_machine.transition(request_id, OrchestratorState.CANCELLED)

    def get_diagnostics(self, request_id: str) -> RequestDiagnostics | None:
        """Retrieve diagnostics container for request_id."""
        with self._lock:
            return self._diagnostics_store.get(request_id)

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return lifecycle manager statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "requests_managed_count": self._requests_managed_count,
                "active_lifecycle_count": len(self._diagnostics_store),
                "thread_safe": True,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose performance metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            message="AIRequestLifecycleManager operational.",
        )
