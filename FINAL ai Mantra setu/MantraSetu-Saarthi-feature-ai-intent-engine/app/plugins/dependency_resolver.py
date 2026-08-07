"""DAG Dependency Graph Resolver & Circular Dependency Detector v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.plugins.plugin_models import PluginDefinition

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "DependencyResolver"
_COMPONENT_VERSION = "1.0.0"


class DependencyResolver:
    """Enterprise thread-safe resolver verifying plugin dependency graphs and detecting circular dependencies."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._resolutions_count = 0

    def resolve_dependencies(
        self,
        plugin_id: str,
        all_plugins: dict[str, PluginDefinition],
    ) -> list[str]:
        """Resolve topological order of required dependencies for plugin_id."""
        with self._lock:
            self._resolutions_count += 1
            visited: set[str] = set()
            order: list[str] = []

            def dfs(curr_id: str):
                if curr_id in visited:
                    return
                visited.add(curr_id)
                plugin = all_plugins.get(curr_id)
                if plugin:
                    for dep in plugin.dependencies:
                        if dep.required_plugin_id in all_plugins:
                            dfs(dep.required_plugin_id)
                order.append(curr_id)

            dfs(plugin_id)
            return order

    def detect_circular_dependencies(
        self,
        all_plugins: dict[str, PluginDefinition],
    ) -> list[list[str]]:
        """Detect circular dependency loops in plugin graph using DFS recursion stack."""
        with self._lock:
            cycles: list[list[str]] = []
            visited: set[str] = set()
            rec_stack: set[str] = set()

            def dfs(curr_id: str, path: list[str]):
                visited.add(curr_id)
                rec_stack.add(curr_id)
                path.append(curr_id)

                plugin = all_plugins.get(curr_id)
                if plugin:
                    for dep in plugin.dependencies:
                        req_id = dep.required_plugin_id
                        if req_id in rec_stack:
                            # Cycle detected
                            cycle_start = path.index(req_id)
                            cycles.append(path[cycle_start:] + [req_id])
                        elif req_id not in visited and req_id in all_plugins:
                            dfs(req_id, list(path))

                rec_stack.remove(curr_id)

            for pid in all_plugins:
                if pid not in visited:
                    dfs(pid, [])

            if cycles:
                logger.warning("DependencyResolver detected %d circular dependency cycles", len(cycles))
            return cycles

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose dependency resolver operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "resolutions_count": self._resolutions_count,
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
