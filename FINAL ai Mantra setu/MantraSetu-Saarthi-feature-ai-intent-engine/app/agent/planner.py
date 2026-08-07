"""Agent Planner Service orchestration layer for MantraSetu AgentOS.

This module implements AgentPlannerService, coordinating autonomous task plan generation requests
with an injected BaseAgentPlanner provider without LLM SDK or browser dependencies.
"""

from __future__ import annotations

from app.agent.base import (
    AgentInitializationError,
    AgentPlanningError,
    BaseAgentPlanner,
)
from app.agent.models import (
    AgentContext,
    AgentPlan,
    AgentTask,
)
from app.core.models import ComponentHealth, SystemHealthStatus


class AgentPlannerService:
    """Service facade coordinating agent task plan generation requests.

    Responsibility:
        Validates AgentTask and AgentContext models, delegates plan generation to an injected
        BaseAgentPlanner provider, translates planning errors into domain exceptions, and manages lifecycle health.
    """

    def __init__(self, planner: BaseAgentPlanner) -> None:
        """Initialize AgentPlannerService with an injected BaseAgentPlanner dependency.

        Args:
            planner: Injected BaseAgentPlanner implementation.
        """
        self._planner = planner
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the planner service has been initialized.

        Raises:
            AgentInitializationError: If initialize() has not been called.
        """
        if not self._initialized:
            raise AgentInitializationError(
                "AgentPlannerService is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize planner service and underlying provider runtime state. Idempotent."""
        if self._initialized:
            return

        if hasattr(self._planner, "initialize"):
            await self._planner.initialize()

        self._initialized = True

    async def close(self) -> None:
        """Close planner service and release provider resources."""
        if hasattr(self._planner, "close"):
            await self._planner.close()

        self._initialized = False

    async def create_plan(
        self,
        task: AgentTask,
        context: AgentContext,
    ) -> AgentPlan:
        """Validate inputs and generate a multi-step AgentPlan via injected planner provider.

        Args:
            task: AgentTask model representing user instruction.
            context: Consolidated AgentContext model.

        Returns:
            AgentPlan: Created multi-step task execution plan entity.

        Raises:
            AgentInitializationError: If service is uninitialized.
            AgentPlanningError: If task or context parameters are invalid or plan generation fails.
        """
        self._require_initialized()
        if not isinstance(task, AgentTask):
            raise AgentPlanningError("Invalid AgentTask instance provided.")
        if not isinstance(context, AgentContext):
            raise AgentPlanningError("Invalid AgentContext instance provided.")
        if not task.user_input or not task.user_input.strip():
            raise AgentPlanningError("AgentTask user_input string cannot be empty or blank.")

        try:
            return await self._planner.create_plan(task, context)
        except AgentPlanningError:
            raise
        except Exception as e:
            raise AgentPlanningError(
                f"Agent plan generation failed for task '{task.task_id}': {str(e)}"
            ) from e

    async def health_check(self) -> ComponentHealth:
        """Check operational health of the agent planner service.

        Returns:
            ComponentHealth: Operational component health status model.
        """
        if not self._initialized:
            return ComponentHealth(
                component_name="agent_planner_service",
                status=SystemHealthStatus.UNHEALTHY,
                message="AgentPlannerService uninitialized.",
            )

        planner_healthy = True
        if hasattr(self._planner, "health_check"):
            res = await self._planner.health_check()
            if isinstance(res, ComponentHealth):
                planner_healthy = res.status == SystemHealthStatus.HEALTHY
            elif isinstance(res, bool):
                planner_healthy = res

        return ComponentHealth(
            component_name="agent_planner_service",
            status=SystemHealthStatus.HEALTHY if planner_healthy else SystemHealthStatus.UNHEALTHY,
            message="AgentPlannerService operational."
            if planner_healthy
            else "AgentPlannerService provider degraded.",
        )
