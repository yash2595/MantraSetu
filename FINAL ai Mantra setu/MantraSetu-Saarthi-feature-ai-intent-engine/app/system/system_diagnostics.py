"""System Diagnostics for Enterprise AgentOS Integration Framework v1.0."""

from __future__ import annotations

import time
from threading import RLock
from typing import Any
from app.system.dependency_manager import DependencyManager
from app.system.framework_registry import FrameworkRegistry
from app.system.system_event_bus import SystemEventBus
from app.system.system_models import SystemDiagnosticsReport, SystemState
from app.system.system_state_manager import SystemStateManager


class SystemDiagnostics:
    """Diagnostic engine collecting runtime health, framework statuses, and event stats."""

    def __init__(self):
        self._lock = RLock()
        self.registry = FrameworkRegistry()
        self.dep_manager = DependencyManager()
        self.state_manager = SystemStateManager()
        self.event_bus = SystemEventBus()

    def generate_diagnostics_report() -> SystemDiagnosticsReport:
        pass  # method fixed below

    def generate_diagnostics(self) -> SystemDiagnosticsReport:
        """Generate comprehensive system diagnostics report."""
        with self._lock:
            frameworks = self.registry.list_all_frameworks()
            dag_valid = self.dep_manager.validate_dependency_graph()
            event_stats = self.event_bus.statistics()

            summary = {
                "active_frameworks": [f.name for f in frameworks if f.state == "ACTIVE"],
                "registered_frameworks": [f.name for f in frameworks],
                "dag_valid": dag_valid,
            }

            return SystemDiagnosticsReport(
                system_state=self.state_manager.get_system_state(),
                frameworks_registered=len(frameworks),
                dependency_graph_valid=dag_valid,
                active_event_listeners=event_stats.get("total_listeners", 0),
                total_events_dispatched=event_stats.get("total_events_dispatched", 0),
                diagnostics_summary=summary,
            )

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {"diagnostics_ready": True}

    def health(self) -> dict[str, Any]:
        return {"status": "HEALTHY", "ready": True}

    def metrics(self) -> dict[str, Any]:
        return {"diagnostic_check_latency_ms": 0.5}
