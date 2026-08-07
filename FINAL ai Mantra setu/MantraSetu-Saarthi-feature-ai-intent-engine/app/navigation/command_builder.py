"""Platform-neutral command builder engine for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any
from uuid import uuid4

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.execution_models import ExecutionCommand, UIActionStep

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "CommandBuilderEngine"
_COMPONENT_VERSION = "4.1"


class CommandBuilderEngine:
    """Engine constructing platform-neutral ExecutionCommand directives from UI action steps."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._commands_built_count = 0

    def build_commands(self, steps: tuple[UIActionStep, ...] | list[UIActionStep]) -> tuple[ExecutionCommand, ...]:
        """Transform validated UIActionStep objects into platform-neutral ExecutionCommand directives."""
        with self._lock:
            commands: list[ExecutionCommand] = []
            idx = 1

            for step in steps:
                cmd_id = f"cmd_{uuid4().hex[:8]}"
                self._commands_built_count += 1
                commands.append(
                    ExecutionCommand(
                        command_id=cmd_id,
                        command_type=step.action_type,
                        target=step.target_element_id,
                        parameters=dict(step.parameters),
                        sequence_index=idx,
                    )
                )
                idx += 1

            return tuple(commands)

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
                "commands_built_count": self._commands_built_count,
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
            message="CommandBuilderEngine operational.",
        )
