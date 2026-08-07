"""Orchestrator Lifecycle State Machine for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.orchestrator.orchestrator_exceptions import ValidationError
from app.orchestrator.orchestrator_models import OrchestratorState

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "OrchestratorStateMachine"
_COMPONENT_VERSION = "4.1"


class OrchestratorStateMachine:
    """Explicit state machine governing valid request lifecycle transitions."""

    _VALID_TRANSITIONS: dict[OrchestratorState, set[OrchestratorState]] = {
        OrchestratorState.IDLE: {
            OrchestratorState.BUILDING_CONTEXT,
            OrchestratorState.FAILED,
            OrchestratorState.CANCELLED,
        },
        OrchestratorState.BUILDING_CONTEXT: {
            OrchestratorState.SELECTING_PROVIDER,
            OrchestratorState.EXECUTING_LLM,
            OrchestratorState.SYNTHESIZING_RESPONSE,
            OrchestratorState.STREAMING,
            OrchestratorState.COMPLETED,
            OrchestratorState.FAILED,
            OrchestratorState.CANCELLED,
        },
        OrchestratorState.SELECTING_PROVIDER: {
            OrchestratorState.EXECUTING_LLM,
            OrchestratorState.STREAMING,
            OrchestratorState.FAILED,
            OrchestratorState.CANCELLED,
            OrchestratorState.COMPLETED,
        },
        OrchestratorState.EXECUTING_LLM: {
            OrchestratorState.ROUTING_TOOLS,
            OrchestratorState.SYNTHESIZING_RESPONSE,
            OrchestratorState.STREAMING,
            OrchestratorState.FAILED,
            OrchestratorState.CANCELLED,
        },
        OrchestratorState.ROUTING_TOOLS: {
            OrchestratorState.SYNTHESIZING_RESPONSE,
            OrchestratorState.EXECUTING_LLM,
            OrchestratorState.FAILED,
            OrchestratorState.CANCELLED,
        },
        OrchestratorState.SYNTHESIZING_RESPONSE: {
            OrchestratorState.COMPLETED,
            OrchestratorState.STREAMING,
            OrchestratorState.FAILED,
            OrchestratorState.CANCELLED,
        },
        OrchestratorState.STREAMING: {
            OrchestratorState.COMPLETED,
            OrchestratorState.FAILED,
            OrchestratorState.CANCELLED,
        },
        OrchestratorState.COMPLETED: set(),
        OrchestratorState.FAILED: set(),
        OrchestratorState.CANCELLED: set(),
    }

    def __init__(self) -> None:
        self._states: dict[str, OrchestratorState] = {}
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._transitions_count = 0

    def init_request(self, request_id: str) -> None:
        """Initialize state machine tracking for a new request_id."""
        with self._lock:
            self._states[request_id] = OrchestratorState.IDLE

    def transition(self, request_id: str, new_state: OrchestratorState) -> OrchestratorState:
        """Validate and execute a state transition for request_id."""
        with self._lock:
            curr = self._states.get(request_id, OrchestratorState.IDLE)
            allowed = self._VALID_TRANSITIONS.get(curr, set())

            if new_state not in allowed:
                err_msg = f"Invalid state transition for request '{request_id}' from '{curr.value}' to '{new_state.value}'."
                logger.error(err_msg)
                raise ValidationError(err_msg, diagnostics={"current_state": curr.value, "target_state": new_state.value})

            self._states[request_id] = new_state
            self._transitions_count += 1
            return new_state

    def get_state(self, request_id: str) -> OrchestratorState:
        """Return active state for request_id."""
        with self._lock:
            return self._states.get(request_id, OrchestratorState.IDLE)

    def cleanup(self, request_id: str) -> None:
        """Remove state tracking for request_id."""
        with self._lock:
            self._states.pop(request_id, None)

    # ------------------------------------------------------------------
    # Diagnostics, Telemetry & Health
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return state machine statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "active_requests_monitored": len(self._states),
                "transitions_count": self._transitions_count,
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
            message="OrchestratorStateMachine operational.",
        )
