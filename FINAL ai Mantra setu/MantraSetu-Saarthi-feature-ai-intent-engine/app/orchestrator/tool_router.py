"""Enterprise Tool Router for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.orchestrator.orchestrator_contracts import IToolRouterBridge
from app.orchestrator.orchestrator_models import ToolInvocation
from app.orchestrator.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "EnterpriseToolRouter"
_COMPONENT_VERSION = "4.1"


class EnterpriseToolRouter(IToolRouterBridge):
    """Tool Router dispatching tool calls using ToolRegistry."""

    def __init__(self, registry: ToolRegistry | None = None) -> None:
        self._registry = registry or ToolRegistry()
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._dispatches_count = 0

    def dispatch(self, invocation: ToolInvocation) -> ToolInvocation:
        """Route tool invocation to target handler based on ToolRegistry lookup."""
        with self._lock:
            self._dispatches_count += 1
            desc = self._registry.get_tool(invocation.tool_name)
            if not desc or not desc.is_available:
                return ToolInvocation(
                    tool_id=invocation.tool_id,
                    category=invocation.category,
                    tool_name=invocation.tool_name,
                    arguments=dict(invocation.arguments),
                    status="FAILED",
                    result=f"Tool '{invocation.tool_name}' is not registered or currently unavailable.",
                )

            # Simulated clean execution of registered tool
            result_payload = {"status": "SUCCESS", "tool": invocation.tool_name, "args": invocation.arguments}
            return ToolInvocation(
                tool_id=invocation.tool_id,
                category=invocation.category,
                tool_name=invocation.tool_name,
                arguments=dict(invocation.arguments),
                status="COMPLETED",
                result=result_payload,
            )

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return tool router statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dispatches_count": self._dispatches_count,
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
            message="EnterpriseToolRouter operational.",
        )
