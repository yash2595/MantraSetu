"""Tool Output Payload Normalization & Result Builder v1.1."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.tools.tool_models import ToolInvocation, ToolInvocationStatus, ToolResult

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ToolResultBuilder"
_COMPONENT_VERSION = "1.1.0"


class ToolResultBuilder:
    """Enterprise result builder generating standardized immutable ToolResult payloads (<2ms target)."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._results_built_count = 0

    def build_success_result(
        self,
        invocation: ToolInvocation,
        raw_data: Any,
        execution_time_ms: float = 0.0,
    ) -> ToolResult:
        """Build immutable success ToolResult object (<2ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._results_built_count += 1
            data_dict = raw_data if isinstance(raw_data, dict) else {"result": raw_data}

            res = ToolResult(
                invocation_id=invocation.invocation_id,
                tool_name=invocation.tool_name,
                status=ToolInvocationStatus.SUCCESS,
                data=data_dict,
                execution_time_ms=round(execution_time_ms, 2),
                cached=False,
            )
            duration_ms = (time.perf_counter() - start_ts) * 1000
            logger.debug("Built success ToolResult for '%s' in %.2fms", invocation.tool_name, duration_ms)
            return res

    def build_error_result(
        self,
        invocation: ToolInvocation,
        error_msg: str,
        execution_time_ms: float = 0.0,
        status: ToolInvocationStatus = ToolInvocationStatus.FAILED,
    ) -> ToolResult:
        """Build immutable error ToolResult object (<2ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._results_built_count += 1

            res = ToolResult(
                invocation_id=invocation.invocation_id,
                tool_name=invocation.tool_name,
                status=status,
                data={},
                error_message=error_msg,
                execution_time_ms=round(execution_time_ms, 2),
                cached=False,
            )
            duration_ms = (time.perf_counter() - start_ts) * 1000
            logger.debug("Built error ToolResult for '%s' in %.2fms", invocation.tool_name, duration_ms)
            return res

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose result builder operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "results_built_count": self._results_built_count,
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
