"""Least-Privilege Plugin Permission & Authorization Manager v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.plugins.plugin_models import PermissionLevel, PluginContext, PluginDefinition
from app.plugins.plugin_telemetry import PluginTelemetryEngine

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "PluginPermissionManager"
_COMPONENT_VERSION = "1.0.0"


class PluginPermissionManager:
    """Enterprise thread-safe manager enforcing least-privilege permission models for plugins."""

    def __init__(self, telemetry: PluginTelemetryEngine | None = None) -> None:
        self._telemetry = telemetry or PluginTelemetryEngine()
        self._lock = RLock()
        self._validations_count = 0

    def validate_permissions(self, plugin: PluginDefinition, context: PluginContext) -> bool:
        """Validate if context granted permissions satisfy plugin required permissions."""
        with self._lock:
            self._validations_count += 1

            # FULL_ACCESS granted permission bypasses all specific checks
            if PermissionLevel.FULL_ACCESS in context.granted_permissions:
                return True

            granted_set = set(context.granted_permissions)
            for req in plugin.required_permissions:
                if req != PermissionLevel.NONE and req not in granted_set:
                    self._telemetry.record_permission_denial()
                    logger.warning("PluginPermissionManager denied execution for plugin '%s': missing '%s'", plugin.plugin_id, req)
                    return False
            return True

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose permission manager operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "validations_count": self._validations_count,
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
