"""System Orchestrator for Enterprise AgentOS Integration Framework v1.0."""

from __future__ import annotations

import time
from threading import RLock
from typing import Any
from app.system.dependency_manager import DependencyManager
from app.system.framework_registry import FrameworkRegistry
from app.system.integration_router import IntegrationRouter
from app.system.shutdown_manager import ShutdownManager
from app.system.startup_manager import StartupManager
from app.system.system_configuration import SystemConfiguration
from app.system.system_diagnostics import SystemDiagnostics
from app.system.system_event_bus import SystemEventBus
from app.system.system_health_manager import SystemHealthManager
from app.system.system_models import SystemEvent, SystemHealthAggregated, SystemState
from app.system.system_state_manager import SystemStateManager
from app.system.system_telemetry import SystemTelemetry


class SystemOrchestrator:
    """Primary system orchestrator coordinating all AgentOS frameworks into a unified runtime."""

    _instance: SystemOrchestrator | None = None
    _lock: RLock = RLock()

    def __new__(cls) -> SystemOrchestrator:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        with self._lock:
            if getattr(self, "_initialized", False):
                return
            self.registry = FrameworkRegistry()
            self.dependency_manager = DependencyManager()
            self.router = IntegrationRouter()
            self.startup_manager = StartupManager()
            self.shutdown_manager = ShutdownManager()
            self.health_manager = SystemHealthManager()
            self.state_manager = SystemStateManager()
            self.event_bus = SystemEventBus()
            self.configuration = SystemConfiguration()
            self.diagnostics = SystemDiagnostics()
            self.telemetry = SystemTelemetry()
            self._initialized = True

    @classmethod
    def reset(cls) -> None:
        """Reset singleton state for isolated testing."""
        with cls._lock:
            if cls._instance:
                cls._instance.registry.reset()
                cls._instance.state_manager.set_system_state(SystemState.UNINITIALIZED)
                cls._instance._initialized = False
                cls._instance = None

    def initialize_and_start(self) -> dict[str, Any]:
        """Start up AgentOS system in dependency order (<5 ms target)."""
        with self._lock:
            self.state_manager.set_system_state(SystemState.STARTING)
            res = self.startup_manager.start_all_frameworks()
            self.state_manager.set_system_state(SystemState.RUNNING)
            self.telemetry.record_metric("system.startup_latency_ms", res.get("duration_ms", 0.0))
            return res

    def shutdown(self) -> dict[str, Any]:
        """Gracefully shut down AgentOS system in reverse dependency order (<5 ms target)."""
        with self._lock:
            self.state_manager.set_system_state(SystemState.SHUTTING_DOWN)
            res = self.shutdown_manager.shutdown_all_frameworks()
            self.state_manager.set_system_state(SystemState.STOPPED)
            self.telemetry.record_metric("system.shutdown_latency_ms", res.get("duration_ms", 0.0))
            return res

    def get_system_health(self) -> SystemHealthAggregated:
        """Aggregate health state across all 15 frameworks (<2 ms target)."""
        return self.health_manager.aggregate_health()

    def route_communication(self, source: str, target: str, action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Route cross-framework message (<3 ms target)."""
        return self.router.route_message(source, target, action, payload)

    def publish_event(self, event: SystemEvent) -> int:
        """Publish system event to bus."""
        return self.event_bus.publish(event)

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "registry": self.registry.statistics(),
                "router": self.router.statistics(),
                "health": self.health_manager.statistics(),
                "event_bus": self.event_bus.statistics(),
                "telemetry": self.telemetry.statistics(),
                "system_state": str(self.state_manager.get_system_state()),
            }

    def health(self) -> dict[str, Any]:
        agg = self.get_system_health()
        return {
            "status": agg.overall_health,
            "system_state": str(agg.system_state),
            "active_frameworks_count": agg.active_frameworks_count,
            "total_frameworks_count": agg.total_frameworks_count,
        }

    def metrics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "startup": self.startup_manager.metrics(),
                "router": self.router.metrics(),
                "health": self.health_manager.metrics(),
            }
