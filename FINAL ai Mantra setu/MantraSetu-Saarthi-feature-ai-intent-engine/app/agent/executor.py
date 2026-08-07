"""Agent Executor Service orchestration layer for MantraSetu AgentOS.

This module implements AgentExecutorService, coordinating autonomous agent plan execution requests
with an injected BaseAgentExecutor provider without LLM SDK or browser dependencies.
"""

from __future__ import annotations

from app.agent.base import (
    AgentExecutionError,
    AgentInitializationError,
    BaseAgentExecutor,
)
from app.agent.models import (
    AgentContext,
    AgentExecutionResult,
    AgentPlan,
)
from app.core.models import ComponentHealth, SystemHealthStatus


class AgentExecutorService:
    """Service facade coordinating agent plan execution requests.

    Responsibility:
        Validates AgentPlan and AgentContext models, delegates step execution to an injected
        BaseAgentExecutor provider, translates execution errors into domain exceptions, and manages lifecycle health.
    """

    def __init__(self, executor: BaseAgentExecutor) -> None:
        """Initialize AgentExecutorService with an injected BaseAgentExecutor dependency.

        Args:
            executor: Injected BaseAgentExecutor implementation.
        """
        self._executor = executor
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the executor service has been initialized.

        Raises:
            AgentInitializationError: If initialize() has not been called.
        """
        if not self._initialized:
            raise AgentInitializationError(
                "AgentExecutorService is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize executor service and underlying provider runtime state. Idempotent."""
        if self._initialized:
            return

        if hasattr(self._executor, "initialize"):
            await self._executor.initialize()

        self._initialized = True

    async def close(self) -> None:
        """Close executor service and release provider resources."""
        if hasattr(self._executor, "close"):
            await self._executor.close()

        self._initialized = False

    async def execute(
        self,
        plan: AgentPlan,
        context: AgentContext,
    ) -> AgentExecutionResult:
        """Validate inputs and execute an AgentPlan via injected executor provider.

        Args:
            plan: AgentPlan model containing ordered step instructions.
            context: Consolidated AgentContext model.

        Returns:
            AgentExecutionResult: Execution outcome domain model.

        Raises:
            AgentInitializationError: If service is uninitialized.
            AgentExecutionError: If plan or context parameters are invalid or execution fails.
        """
        self._require_initialized()
        if not isinstance(plan, AgentPlan):
            raise AgentExecutionError("Invalid AgentPlan instance provided.")
        if not isinstance(context, AgentContext):
            raise AgentExecutionError("Invalid AgentContext instance provided.")
        if not plan.steps:
            raise AgentExecutionError("AgentPlan steps tuple cannot be empty.")

        try:
            return await self._executor.execute(plan, context)
        except AgentExecutionError:
            raise
        except Exception as e:
            raise AgentExecutionError(
                f"Agent plan execution failed for plan '{plan.plan_id}': {str(e)}"
            ) from e

    async def health_check(self) -> ComponentHealth:
        """Check operational health of the agent executor service.

        Returns:
            ComponentHealth: Operational component health status model.
        """
        if not self._initialized:
            return ComponentHealth(
                component_name="agent_executor_service",
                status=SystemHealthStatus.UNHEALTHY,
                message="AgentExecutorService uninitialized.",
            )

        executor_healthy = True
        if hasattr(self._executor, "health_check"):
            res = await self._executor.health_check()
            if isinstance(res, ComponentHealth):
                executor_healthy = res.status == SystemHealthStatus.HEALTHY
            elif isinstance(res, bool):
                executor_healthy = res

        return ComponentHealth(
            component_name="agent_executor_service",
            status=SystemHealthStatus.HEALTHY if executor_healthy else SystemHealthStatus.UNHEALTHY,
            message="AgentExecutorService operational."
            if executor_healthy
            else "AgentExecutorService provider degraded.",
        )
