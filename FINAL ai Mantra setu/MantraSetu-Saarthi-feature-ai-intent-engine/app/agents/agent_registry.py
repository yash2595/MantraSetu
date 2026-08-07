"""Central Enterprise Registry for Specialized AI Agents v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.agents.agent_models import AgentDefinition, AgentRole, AgentType

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "AgentRegistry"
_COMPONENT_VERSION = "1.0.0"


class AgentRegistry:
    """Enterprise thread-safe registry storing specialized AI worker definitions, capabilities, and roles."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentDefinition] = {}
        self._lock = RLock()
        self._registration_count = 0
        self._register_default_agents()

    def _register_default_agents(self) -> None:
        """Register default specialized worker agents."""
        # 1. Search Specialist Agent
        search_agent = AgentDefinition(
            agent_id="search_agent_01",
            name="Search Specialist Agent",
            agent_type=AgentType.SPECIALIST,
            role=AgentRole.SEARCH_AGENT,
            capabilities=["SEMANTIC_SEARCH", "CATALOG_QUERY"],
        )
        self.register_agent(search_agent)

        # 2. Puja Booking Agent
        puja_agent = AgentDefinition(
            agent_id="puja_agent_01",
            name="Puja Booking Specialist Agent",
            agent_type=AgentType.SPECIALIST,
            role=AgentRole.PUJA_AGENT,
            capabilities=["PUJA_SELECTION", "PANDIT_MATCHING", "BOOKING_SLOT"],
        )
        self.register_agent(puja_agent)

        # 3. Kundali Astrology Agent
        kundali_agent = AgentDefinition(
            agent_id="kundali_agent_01",
            name="Vedic Kundali Astrology Agent",
            agent_type=AgentType.SPECIALIST,
            role=AgentRole.KUNDALI_AGENT,
            capabilities=["HOROSCOPE_ANALYSIS", "MUHURAT_CALCULATION"],
        )
        self.register_agent(kundali_agent)

        # 4. Voice Form Automation Agent
        form_agent = AgentDefinition(
            agent_id="form_agent_01",
            name="Voice Form Automation Agent",
            agent_type=AgentType.SPECIALIST,
            role=AgentRole.FORM_AGENT,
            capabilities=["FIELD_MAPPING", "FORM_VALIDATION"],
        )
        self.register_agent(form_agent)

        # 5. Auditor Agent
        auditor_agent = AgentDefinition(
            agent_id="auditor_agent_01",
            name="Governance & Auditor Agent",
            agent_type=AgentType.VALIDATOR,
            role=AgentRole.AUDITOR,
            capabilities=["POLICY_CHECK", "SAFETY_AUDIT"],
        )
        self.register_agent(auditor_agent)

    def register_agent(self, definition: AgentDefinition) -> None:
        """Register or update an agent definition."""
        with self._lock:
            self._registration_count += 1
            self._agents[definition.agent_id] = definition
            logger.info("AgentRegistry registered agent '%s' (%s - %s)", definition.name, definition.agent_id, definition.role)

    def get_agent(self, agent_id: str) -> AgentDefinition | None:
        """Get AgentDefinition by agent_id."""
        with self._lock:
            return self._agents.get(agent_id)

    def find_by_role(self, role: AgentRole) -> list[AgentDefinition]:
        """Filter registered agents by AgentRole."""
        with self._lock:
            return [a for a in self._agents.values() if a.role == role]

    def find_by_capability(self, capability: str) -> list[AgentDefinition]:
        """Find agents matching a target capability string."""
        with self._lock:
            cap_clean = capability.upper()
            return [a for a in self._agents.values() if cap_clean in [c.upper() for c in a.capabilities]]

    def list_all_agents(self) -> list[AgentDefinition]:
        """Return defensive list of all registered agents."""
        with self._lock:
            return list(self._agents.values())

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose agent registry operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "registered_agents_count": len(self._agents),
                "registration_events_count": self._registration_count,
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
