"""Central Dynamic Plugin Registry v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.plugins.plugin_models import (
    PermissionLevel,
    PluginCapability,
    PluginCategory,
    PluginDefinition,
    PluginType,
)

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "PluginRegistry"
_COMPONENT_VERSION = "1.0.0"


class PluginRegistry:
    """Enterprise thread-safe registry storing plugin definitions, metadata, categories, and capabilities (<2ms target)."""

    def __init__(self) -> None:
        self._plugins: dict[str, PluginDefinition] = {}
        self._lock = RLock()
        self._registrations_count = 0
        self._register_default_plugins()

    def _register_default_plugins(self) -> None:
        """Register default system built-in extension plugins."""
        # 1. Vedic Astrology Extension Plugin
        astro_plugin = PluginDefinition(
            plugin_id="astro_calc_plugin_01",
            name="Vedic Astrology Kundali Plugin",
            version="1.0.0",
            plugin_type=PluginType.BUILTIN,
            category=PluginCategory.ASTROLOGY,
            capabilities=[PluginCapability(name="KUNDALI_CHART", description="Generates Kundali Chart")],
            required_permissions=[PermissionLevel.EXECUTE],
        )
        self.register_plugin(astro_plugin)

        # 2. Puja Ritual Assistant Plugin
        puja_plugin = PluginDefinition(
            plugin_id="puja_ritual_plugin_01",
            name="Puja Ritual Assistant Plugin",
            version="1.0.0",
            plugin_type=PluginType.BUILTIN,
            category=PluginCategory.PUJA,
            capabilities=[PluginCapability(name="RITUAL_GUIDE", description="Provides Puja Steps")],
            required_permissions=[PermissionLevel.EXECUTE],
        )
        self.register_plugin(puja_plugin)

    def register_plugin(self, definition: PluginDefinition) -> None:
        """Register or update a PluginDefinition (<2ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._registrations_count += 1
            self._plugins[definition.plugin_id] = definition
            duration_ms = (time.perf_counter() - start_ts) * 1000
            logger.info("PluginRegistry registered plugin '%s' (%s) in %.2fms", definition.name, definition.plugin_id, duration_ms)

    def get_plugin(self, plugin_id: str) -> PluginDefinition | None:
        """Retrieve PluginDefinition by plugin_id (<2ms target)."""
        with self._lock:
            return self._plugins.get(plugin_id)

    def list_by_category(self, category: PluginCategory) -> list[PluginDefinition]:
        """Filter registered plugins by PluginCategory."""
        with self._lock:
            return [p for p in self._plugins.values() if p.category == category]

    def list_all_plugins(self) -> list[PluginDefinition]:
        """Return defensive list of all registered plugins."""
        with self._lock:
            return list(self._plugins.values())

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose plugin registry operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "registered_plugins_count": len(self._plugins),
                "registrations_count": self._registrations_count,
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
