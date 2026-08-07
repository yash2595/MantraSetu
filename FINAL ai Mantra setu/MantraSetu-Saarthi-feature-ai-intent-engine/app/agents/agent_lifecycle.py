"""Enterprise Agent Lifecycle & Health Manager v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.agents.agent_models import AgentState
from app.agents.agent_registry import AgentRegistry

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "AgentLifecycleManager"
_COMPONENT_VERSION = "1.0.0"


class AgentLifecycleManager:
    """Enterprise thread-safe manager controlling agent state transitions (IDLE, BUSY, PAUSED, OFFLINE) and health checks."""

    def __init__(self, registry: AgentRegistry | None = None) -> None:
        self._registry = registry or AgentRegistry()
        self._lock = RLock()
        self._lifecycle_events_count = 0

    def start_agent(self, agent_id: str) -> bool:
        """Start or wake an agent to IDLE state."""
        with self._lock:
            self._lifecycle_events_count += 1
            agent = self._registry.get_agent(agent_id)
            if agent:
                agent.state = AgentState.IDLE
                logger.info("LifecycleManager started agent '%s'", agent_id)
                return True
            return False

    def pause_agent(self, agent_id: str) -> bool:
        """Pause an agent."""
        with self._lock:
            self._lifecycle_events_count += 1
            agent = self._registry.get_agent(agent_id)
            if agent:
                agent.state = AgentState.PAUSED
                logger.info("LifecycleManager paused agent '%s'", agent_id)
                return True
            return False

    def resume_agent(self, agent_id: str) -> bool:
        """Resume a paused agent to IDLE state."""
        with self._lock:
            self._lifecycle_events_count += 1
            return self.start_agent(agent_id)

    def shutdown_agent(self, agent_id: str) -> bool:
        """Shutdown an agent to OFFLINE state."""
        with self._lock:
            self._lifecycle_events_count += 1
            agent = self._registry.get_agent(agent_id)
            if agent:
                agent.state = AgentState.OFFLINE
                logger.info("LifecycleManager shut down agent '%s'", agent_id)
                return True
            return False

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose lifecycle manager operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "lifecycle_events_count": self._lifecycle_events_count,
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
