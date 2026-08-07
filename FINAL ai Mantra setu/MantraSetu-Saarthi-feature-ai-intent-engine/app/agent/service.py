"""Agent Core Application Service Facade for MantraSetu AgentOS.

This module implements AgentService as the main application facade for the Agent Core subsystem,
orchestrating context creation, plan generation, and plan execution pipelines for autonomous tasks.
"""

from __future__ import annotations

from uuid import UUID

from app.agent.base import (
    AgentError,
    AgentExecutionError,
    AgentInitializationError,
)
from app.agent.context import AgentContextService
from app.agent.executor import AgentExecutorService
from app.agent.models import (
    AgentContext,
    AgentExecutionResult,
    AgentTask,
)
from app.agent.planner import AgentPlannerService
from app.core.models import ComponentHealth, SystemHealthStatus


class AgentService:
    """Application facade service coordinating Agent Core subsystem components.

    Responsibility:
        Orchestrates the full agent execution pipeline — context creation, plan generation,
        plan execution, and context retrieval — by coordinating injected AgentPlannerService,
        AgentExecutorService, and AgentContextService dependencies.
    """

    def __init__(
        self,
        planner_service: AgentPlannerService,
        executor_service: AgentExecutorService,
        context_service: AgentContextService,
    ) -> None:
        """Initialize AgentService with strictly injected subsystem dependencies.

        Args:
            planner_service: Injected AgentPlannerService instance.
            executor_service: Injected AgentExecutorService instance.
            context_service: Injected AgentContextService instance.
        """
        self._planner_service = planner_service
        self._executor_service = executor_service
        self._context_service = context_service
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the agent service has been initialized.

        Raises:
            AgentInitializationError: If initialize() has not been called.
        """
        if not self._initialized:
            raise AgentInitializationError(
                "AgentService is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize agent service and all underlying subsystem dependencies. Idempotent."""
        if self._initialized:
            return

        if hasattr(self._planner_service, "initialize"):
            await self._planner_service.initialize()
        if hasattr(self._executor_service, "initialize"):
            await self._executor_service.initialize()
        if hasattr(self._context_service, "initialize"):
            await self._context_service.initialize()

        self._initialized = True

    async def close(self) -> None:
        """Close agent service and release all subsystem resources."""
        if hasattr(self._context_service, "close"):
            await self._context_service.close()
        if hasattr(self._executor_service, "close"):
            await self._executor_service.close()
        if hasattr(self._planner_service, "close"):
            await self._planner_service.close()

        self._initialized = False

    async def run(
        self,
        task: AgentTask,
        conversation_id: UUID | None = None,
        session_id: UUID | None = None,
    ) -> AgentExecutionResult:
        """Execute the full agent pipeline for an AgentTask.

        Pipeline:
            1. Create AgentContext from task_id, conversation_id, session_id.
            2. Generate AgentPlan via AgentPlannerService.
            3. Execute AgentPlan via AgentExecutorService.
            4. Return AgentExecutionResult.

        Args:
            task: AgentTask model representing user instruction.
            conversation_id: Optional associated conversation identifier UUID.
            session_id: Optional associated user session identifier UUID.

        Returns:
            AgentExecutionResult: Execution outcome domain model.

        Raises:
            AgentInitializationError: If service is uninitialized.
            AgentError: If task is invalid or any pipeline stage fails.
        """
        self._require_initialized()
        if not isinstance(task, AgentTask):
            raise AgentError("Invalid AgentTask instance provided.")
        if not task.user_input or not task.user_input.strip():
            raise AgentError("AgentTask user_input string cannot be empty or blank.")

        try:
            # Step 1: Create context
            context = await self._context_service.create_context(
                task_id=task.task_id,
                conversation_id=conversation_id,
                session_id=session_id,
            )

            # Step 2: Generate plan
            plan = await self._planner_service.create_plan(task, context)

            # Step 3: Execute plan
            result = await self._executor_service.execute(plan, context)

            return result

        except (AgentError, AgentExecutionError):
            raise
        except Exception as e:
            raise AgentError(
                f"AgentService pipeline failed for task '{task.task_id}': {str(e)}"
            ) from e

    async def get_context(self, task_id: UUID) -> AgentContext:
        """Retrieve the active AgentContext for a given task_id.

        Args:
            task_id: Associated AgentTask identifier UUID.

        Returns:
            AgentContext: Retrieved agent context model.

        Raises:
            AgentInitializationError: If service is uninitialized.
            AgentError: If task_id is invalid or context is not found.
        """
        self._require_initialized()
        if not isinstance(task_id, UUID):
            raise AgentError("Invalid task_id UUID provided.")

        try:
            return await self._context_service.get_context(task_id)
        except AgentError:
            raise
        except Exception as e:
            raise AgentError(
                f"Failed to retrieve AgentContext for task '{task_id}': {str(e)}"
            ) from e

    async def health_check(self) -> ComponentHealth:
        """Check aggregated operational health across all Agent Core subsystem services.

        Returns:
            ComponentHealth: Aggregated component health status model.
        """
        if not self._initialized:
            return ComponentHealth(
                component_name="agent_service",
                status=SystemHealthStatus.UNHEALTHY,
                message="AgentService uninitialized.",
            )

        planner_health = await self._planner_service.health_check()
        executor_health = await self._executor_service.health_check()
        context_health = await self._context_service.health_check()

        is_healthy = (
            isinstance(planner_health, ComponentHealth)
            and planner_health.status == SystemHealthStatus.HEALTHY
            and isinstance(executor_health, ComponentHealth)
            and executor_health.status == SystemHealthStatus.HEALTHY
            and isinstance(context_health, ComponentHealth)
            and context_health.status == SystemHealthStatus.HEALTHY
        )

        return ComponentHealth(
            component_name="agent_service",
            status=SystemHealthStatus.HEALTHY if is_healthy else SystemHealthStatus.UNHEALTHY,
            message="AgentService operational."
            if is_healthy
            else "AgentService subsystem component degraded.",
        )
