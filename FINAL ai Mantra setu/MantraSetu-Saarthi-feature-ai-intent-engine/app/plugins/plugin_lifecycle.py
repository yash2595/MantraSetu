"""Enterprise Plugin Lifecycle Transition Manager v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.plugins.plugin_models import PluginState
from app.plugins.plugin_registry import PluginRegistry

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "PluginLifecycleManager"
_COMPONENT_VERSION = "1.0.0"


class PluginLifecycleManager:
    """Enterprise thread-safe manager controlling plugin state transitions (REGISTERED, LOADED, ACTIVE, PAUSED, DISABLED, FAILED)."""

    def __init__(self, registry: PluginRegistry | None = None) -> None:
        self._registry = registry or PluginRegistry()
        self._lock = RLock()
        self._transitions_count = 0

    def transition_state(self, plugin_id: str, target_state: PluginState) -> bool:
        """Transition plugin to target PluginState."""
        with self._lock:
            self._transitions_count += 1
            plugin = self._registry.get_plugin(plugin_id)
            if not plugin:
                return False

            old_state = plugin.state
            plugin.state = target_state
            logger.info("PluginLifecycleManager transitioned '%s' [%s -> %s]", plugin_id, old_state, target_state)
            return True

    def get_state(self, plugin_id: str) -> PluginState:
        """Retrieve active state for plugin_id."""
        with self._lock:
            plugin = self._registry.get_plugin(plugin_id)
            return plugin.state if plugin else PluginState.UNLOADED

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose plugin lifecycle manager operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "transitions_count": self._transitions_count,
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
