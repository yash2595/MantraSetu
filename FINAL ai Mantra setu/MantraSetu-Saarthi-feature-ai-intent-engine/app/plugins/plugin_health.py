"""Plugin Health Monitor & Heartbeat Collector v1.0."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.plugins.plugin_models import PluginHealth, PluginState

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "PluginHealthMonitor"
_COMPONENT_VERSION = "1.0.0"


class PluginHealthMonitor:
    """Enterprise thread-safe monitor tracking plugin heartbeats and health snapshots (<2ms target)."""

    def __init__(self) -> None:
        self._health_snapshots: dict[str, PluginHealth] = {}
        self._lock = RLock()
        self._heartbeats_count = 0

    def record_heartbeat(
        self,
        plugin_id: str,
        state: PluginState = PluginState.ACTIVE,
        error_count: int = 0,
    ) -> PluginHealth:
        """Record heartbeat and health snapshot for a plugin (<2ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._heartbeats_count += 1
            now_iso = datetime.now(timezone.utc).isoformat()

            snap = PluginHealth(
                plugin_id=plugin_id,
                state=state,
                last_heartbeat=now_iso,
                error_count=error_count,
            )
            self._health_snapshots[plugin_id] = snap

            duration_ms = (time.perf_counter() - start_ts) * 1000
            logger.debug("PluginHealthMonitor recorded heartbeat for '%s' in %.2fms", plugin_id, duration_ms)
            return snap

    def get_plugin_health(self, plugin_id: str) -> PluginHealth | None:
        """Retrieve health snapshot for plugin_id (<2ms target)."""
        with self._lock:
            return self._health_snapshots.get(plugin_id)

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose health monitor operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "monitored_plugins_count": len(self._health_snapshots),
                "heartbeats_count": self._heartbeats_count,
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
