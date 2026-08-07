"""Plugin Execution Result Normalization Builder v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any
from uuid import uuid4

from app.core.models import ComponentHealth, SystemHealthStatus
from app.plugins.plugin_models import PluginResult

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "PluginResultBuilder"
_COMPONENT_VERSION = "1.0.0"


class PluginResultBuilder:
    """Enterprise thread-safe builder creating normalized PluginResult frames."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._results_built_count = 0

    def build_success(
        self,
        request_id: str,
        plugin_id: str,
        data: dict[str, Any],
        execution_time_ms: float = 0.0,
    ) -> PluginResult:
        """Construct a successful PluginResult object."""
        with self._lock:
            self._results_built_count += 1
            return PluginResult(
                result_id=f"res_{uuid4().hex[:8]}",
                request_id=request_id,
                plugin_id=plugin_id,
                is_success=True,
                data=dict(data),
                execution_time_ms=round(execution_time_ms, 2),
            )

    def build_error(
        self,
        request_id: str,
        plugin_id: str,
        error_msg: str,
        execution_time_ms: float = 0.0,
    ) -> PluginResult:
        """Construct an error PluginResult object."""
        with self._lock:
            self._results_built_count += 1
            return PluginResult(
                result_id=f"res_{uuid4().hex[:8]}",
                request_id=request_id,
                plugin_id=plugin_id,
                is_success=False,
                error_message=error_msg,
                execution_time_ms=round(execution_time_ms, 2),
            )

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
