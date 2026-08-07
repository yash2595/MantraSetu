"""Thread-Pool Parallel Plugin Executor & Task Scheduler v1.0."""

from __future__ import annotations

import concurrent.futures
import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.plugins.plugin_cache import PluginCache
from app.plugins.plugin_models import PluginDefinition, PluginRequest, PluginResult
from app.plugins.plugin_permission_manager import PluginPermissionManager
from app.plugins.plugin_registry import PluginRegistry
from app.plugins.plugin_result_builder import PluginResultBuilder
from app.plugins.plugin_telemetry import PluginTelemetryEngine
from app.plugins.sandbox_runtime import SandboxRuntime

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "PluginExecutor"
_COMPONENT_VERSION = "1.0.0"


class PluginExecutor:
    """Enterprise thread-safe executor running plugin actions sequentially or in parallel thread pools (<5ms routing target)."""

    def __init__(
        self,
        registry: PluginRegistry | None = None,
        permission_manager: PluginPermissionManager | None = None,
        sandbox: SandboxRuntime | None = None,
        result_builder: PluginResultBuilder | None = None,
        cache: PluginCache | None = None,
        telemetry: PluginTelemetryEngine | None = None,
    ) -> None:
        self._registry = registry or PluginRegistry()
        self._permission_manager = permission_manager or PluginPermissionManager()
        self._sandbox = sandbox or SandboxRuntime()
        self._result_builder = result_builder or PluginResultBuilder()
        self._cache = cache or PluginCache()
        self._telemetry = telemetry or PluginTelemetryEngine()

        self._lock = RLock()
        self._executions_count = 0

    def execute_plugin(self, request: PluginRequest) -> PluginResult:
        """Execute a plugin action request (<5ms routing target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._executions_count += 1

            # 1. Check cache
            cached = self._cache.get(request.request_id)
            if cached:
                return cached

            # 2. Get plugin definition
            plugin = self._registry.get_plugin(request.plugin_id)
            if not plugin:
                duration_ms = (time.perf_counter() - start_ts) * 1000
                res = self._result_builder.build_error(
                    request.request_id,
                    request.plugin_id,
                    f"Plugin '{request.plugin_id}' not registered",
                    duration_ms,
                )
                self._telemetry.record_plugin_executed(request.plugin_id, duration_ms, is_success=False)
                return res

            # 3. Validate permissions
            if not self._permission_manager.validate_permissions(plugin, request.context):
                duration_ms = (time.perf_counter() - start_ts) * 1000
                res = self._result_builder.build_error(
                    request.request_id,
                    request.plugin_id,
                    f"Permission denied for plugin '{request.plugin_id}'",
                    duration_ms,
                )
                self._telemetry.record_plugin_executed(request.plugin_id, duration_ms, is_success=False)
                return res

            # 4. Execute in isolated sandbox
            sandbox_output = self._sandbox.execute_in_sandbox(request, request.context.granted_permissions)
            duration_ms = (time.perf_counter() - start_ts) * 1000

            res = self._result_builder.build_success(
                request.request_id,
                request.plugin_id,
                sandbox_output,
                duration_ms,
            )
            self._cache.set(request.request_id, res)
            self._telemetry.record_plugin_executed(request.plugin_id, duration_ms, is_success=True)

            logger.info("PluginExecutor executed plugin '%s' in %.2fms", request.plugin_id, duration_ms)
            return res

    def execute_parallel(
        self,
        requests: list[PluginRequest],
        max_workers: int = 4,
    ) -> list[PluginResult]:
        """Execute multiple plugin requests concurrently in a thread pool."""
        results: list[PluginResult] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.execute_plugin, req) for req in requests]
            for future in concurrent.futures.as_completed(futures):
                try:
                    res = future.result()
                    results.append(res)
                except Exception as e:
                    logger.error("Parallel plugin execution failed: %s", e)

        return results

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose plugin executor operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "executions_count": self._executions_count,
                "telemetry": self._telemetry.statistics(),
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
