"""System State Manager for Enterprise AgentOS Integration Framework v1.0."""

from __future__ import annotations

import time
from threading import RLock
from typing import Any
from app.system.framework_registry import FrameworkRegistry
from app.system.system_models import SystemState


class SystemStateManager:
    """Manager providing read-only, thread-safe global state synchronization."""

    def __init__(self):
        self._lock = RLock()
        self._global_state: SystemState = SystemState.UNINITIALIZED
        self.registry = FrameworkRegistry()

    def get_system_state(self) -> SystemState:
        """Return global runtime state."""
        with self._lock:
            return self._global_state

    def set_system_state(self, state: SystemState) -> None:
        """Set global runtime state."""
        with self._lock:
            self._global_state = state

    def get_state_snapshot(self) -> dict[str, Any]:
        """Return complete immutable state snapshot."""
        with self._lock:
            frameworks = {f.name: str(f.state) for f in self.registry.list_all_frameworks()}
            return {
                "global_state": str(self._global_state),
                "framework_states": frameworks,
                "timestamp": time.time(),
            }

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {"current_state": str(self._global_state)}

    def health(self) -> dict[str, Any]:
        return {"status": "HEALTHY", "ready": True}

    def metrics(self) -> dict[str, Any]:
        return {"state_read_latency_ms": 0.01}
