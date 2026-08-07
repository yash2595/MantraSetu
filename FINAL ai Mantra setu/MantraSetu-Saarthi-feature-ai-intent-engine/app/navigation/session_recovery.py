"""Session recovery and state restoration engine for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.execution_models import ExecutionDirective, ExecutionLifecycleState

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "SessionRecoveryEngine"
_COMPONENT_VERSION = "4.1"


@dataclass(frozen=True)
class SessionRecoveryResult:
    """Immutable result returned by SessionRecoveryEngine."""

    session_id: str
    is_recovered: bool
    pending_directives: tuple[ExecutionDirective, ...] = field(default_factory=tuple)
    last_known_route: str = "/"
    recovery_reason: str = ""
    diagnostics: dict[str, Any] = field(default_factory=dict)


class SessionRecoveryEngine:
    """Engine handling session state restoration and pending directive recovery."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._recoveries_count = 0

    def recover_session_execution(
        self,
        session_id: str,
        last_known_route: str = "/",
        pending_directives: tuple[ExecutionDirective, ...] | list[ExecutionDirective] = (),
        interruption_cause: str = "BROWSER_REFRESH",
    ) -> SessionRecoveryResult:
        """Synthesize a SessionRecoveryResult to resume execution after disconnection or state loss."""
        with self._lock:
            self._recoveries_count += 1
            directives = list(pending_directives)
            recovered_directives = []

            for d in directives:
                # Reset FAILED or WAITING directives to CREATED for re-execution
                if d.status in (ExecutionLifecycleState.FAILED, ExecutionLifecycleState.WAITING, ExecutionLifecycleState.RUNNING):
                    recovered_directives.append(
                        ExecutionDirective(
                            directive_id=d.directive_id,
                            action=d.action,
                            target=d.target,
                            path_sequence=d.path_sequence,
                            parameters=dict(d.parameters),
                            status=ExecutionLifecycleState.CREATED,
                            created_at=d.created_at,
                        )
                    )
                else:
                    recovered_directives.append(d)

            return SessionRecoveryResult(
                session_id=session_id,
                is_recovered=True,
                pending_directives=tuple(recovered_directives),
                last_known_route=last_known_route,
                recovery_reason=f"Session execution recovered after {interruption_cause}.",
                diagnostics={"recovered_count": len(recovered_directives)},
            )

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return diagnostic statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "recoveries_count": self._recoveries_count,
                "thread_safe": True,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose performance metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            message="SessionRecoveryEngine operational.",
        )
