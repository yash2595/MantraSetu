"""Capability Matching, Load Balancing & Failover Router v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.agents.agent_models import AgentDefinition, AgentRole, AgentTask
from app.agents.agent_registry import AgentRegistry

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "AgentRouter"
_COMPONENT_VERSION = "1.0.0"


class AgentRouter:
    """Enterprise thread-safe router assigning tasks to optimal worker agents based on capabilities and roles (<2ms target)."""

    def __init__(self, registry: AgentRegistry | None = None) -> None:
        self._registry = registry or AgentRegistry()
        self._lock = RLock()
        self._routings_count = 0
        self._failover_count = 0

    def route_task(
        self,
        task: AgentTask,
        preferred_role: AgentRole | None = None,
    ) -> AgentDefinition | None:
        """Route an AgentTask to an available specialized worker agent (<2ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._routings_count += 1

            # 1. Match by preferred role if provided
            if preferred_role:
                role_candidates = self._registry.find_by_role(preferred_role)
                if role_candidates:
                    duration_ms = (time.perf_counter() - start_ts) * 1000
                    logger.debug("AgentRouter matched task '%s' to role '%s' in %.2fms", task.task_id, preferred_role, duration_ms)
                    return role_candidates[0]

            # 2. Match by goal payload heuristics
            goal_type = task.payload.get("goal_type", "")
            if "PUJA" in goal_type or "PANDIT" in goal_type:
                candidates = self._registry.find_by_role(AgentRole.PUJA_AGENT)
            elif "KUNDALI" in goal_type:
                candidates = self._registry.find_by_role(AgentRole.KUNDALI_AGENT)
            else:
                candidates = self._registry.find_by_role(AgentRole.SEARCH_AGENT)

            if candidates:
                duration_ms = (time.perf_counter() - start_ts) * 1000
                return candidates[0]

            # Fallback to any available registered agent
            all_agents = self._registry.list_all_agents()
            return all_agents[0] if all_agents else None

    def get_failover_agent(self, failed_agent_id: str) -> AgentDefinition | None:
        """Find a backup failover worker agent when primary agent fails."""
        with self._lock:
            self._failover_count += 1
            primary = self._registry.get_agent(failed_agent_id)
            if not primary:
                return None

            candidates = self._registry.find_by_role(primary.role)
            fallbacks = [a for a in candidates if a.agent_id != failed_agent_id]
            return fallbacks[0] if fallbacks else None

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose router operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "routings_count": self._routings_count,
                "failover_count": self._failover_count,
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
