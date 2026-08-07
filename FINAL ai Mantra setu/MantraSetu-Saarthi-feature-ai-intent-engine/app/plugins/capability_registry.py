"""Dynamic Capability Directory & Plugin Lookup Engine v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.plugins.plugin_models import PluginCapability, PluginDefinition
from app.plugins.plugin_registry import PluginRegistry

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "CapabilityRegistry"
_COMPONENT_VERSION = "1.0.0"


class CapabilityRegistry:
    """Enterprise thread-safe registry mapping capabilities to provider plugins (<2ms target)."""

    def __init__(self, plugin_registry: PluginRegistry | None = None) -> None:
        self._plugin_registry = plugin_registry or PluginRegistry()
        # cap_name -> list of plugin_ids
        self._capability_map: dict[str, list[str]] = {}
        self._lock = RLock()
        self._lookups_count = 0

    def register_capability(self, plugin_id: str, capability: PluginCapability) -> None:
        """Associate a capability name with a provider plugin_id."""
        with self._lock:
            cap_name = capability.name.upper().strip()
            if cap_name not in self._capability_map:
                self._capability_map[cap_name] = []
            if plugin_id not in self._capability_map[cap_name]:
                self._capability_map[cap_name].append(plugin_id)
            logger.info("CapabilityRegistry mapped capability '%s' to plugin '%s'", cap_name, plugin_id)

    def find_plugins_by_capability(self, capability_name: str) -> list[PluginDefinition]:
        """Find registered plugins offering target capability (<2ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._lookups_count += 1
            cap_clean = capability_name.upper().strip()
            plugin_ids = self._capability_map.get(cap_clean, [])

            results: list[PluginDefinition] = []
            for pid in plugin_ids:
                p = self._plugin_registry.get_plugin(pid)
                if p:
                    results.append(p)

            # Fallback search across all registered plugins
            if not results:
                for p in self._plugin_registry.list_all_plugins():
                    for c in p.capabilities:
                        if c.name.upper() == cap_clean and p not in results:
                            results.append(p)

            duration_ms = (time.perf_counter() - start_ts) * 1000
            logger.debug("CapabilityRegistry found %d plugins for capability '%s' in %.2fms", len(results), capability_name, duration_ms)
            return results

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose capability registry operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "capabilities_mapped_count": len(self._capability_map),
                "lookups_count": self._lookups_count,
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
