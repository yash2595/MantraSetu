"""Master Orchestrator Supervisor Agent Engine v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.agents.agent_executor import AgentExecutor
from app.agents.agent_models import AgentDefinition, AgentRole, AgentType
from app.agents.agent_registry import AgentRegistry
from app.agents.agent_router import AgentRouter
from app.agents.result_aggregator import ResultAggregator
from app.agents.task_planner import TaskPlanner

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "SupervisorAgent"
_COMPONENT_VERSION = "1.0.0"


class SupervisorAgent:
    """Master supervisor agent receiving complex goals, decomposing into DAG tasks, routing to workers, and aggregating results."""

    def __init__(
        self,
        registry: AgentRegistry | None = None,
        planner: TaskPlanner | None = None,
        router: AgentRouter | None = None,
        executor: AgentExecutor | None = None,
        aggregator: ResultAggregator | None = None,
    ) -> None:
        self._registry = registry or AgentRegistry()
        self._planner = planner or TaskPlanner()
        self._router = router or AgentRouter(self._registry)
        self._executor = executor or AgentExecutor()
        self._aggregator = aggregator or ResultAggregator()

        self._lock = RLock()
        self._goals_executed_count = 0

    def execute_goal(
        self,
        user_id: str,
        session_id: str,
        goal: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a complex multi-agent user goal (<15ms framework coordination overhead)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._goals_executed_count += 1
            context = context or {}

            # 1. Decompose goal into execution plan
            plan = self._planner.create_execution_plan(goal, context)

            # 2. Route tasks and execute via worker agents
            task_pairs = []
            for task in plan.tasks:
                worker_agent = self._router.route_task(task)
                if not worker_agent:
                    worker_agent = AgentDefinition(name="Fallback Agent", role=AgentRole.SEARCH_AGENT)
                task_pairs.append((task, worker_agent))

            # 3. Execute tasks (sequential or parallel)
            if plan.is_parallel and len(task_pairs) > 1:
                responses = self._executor.execute_parallel(task_pairs)
            else:
                responses = [self._executor.execute_task(t, a) for t, a in task_pairs]

            # 4. Aggregate worker results
            final_output = self._aggregator.aggregate_results(responses)

            duration_ms = (time.perf_counter() - start_ts) * 1000
            final_output["total_coordination_time_ms"] = round(duration_ms, 2)

            logger.info("SupervisorAgent completed goal '%s' with %d tasks in %.2fms", goal[:30], len(plan.tasks), duration_ms)
            return final_output

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose supervisor agent operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "goals_executed_count": self._goals_executed_count,
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
