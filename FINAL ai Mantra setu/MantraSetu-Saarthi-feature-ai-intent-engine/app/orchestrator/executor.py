"""Execution Manager Service for MantraSetu AgentOS.

This module implements ExecutionManager as the downstream service execution coordination
layer for the Orchestrator subsystem, remaining provider independent through the
BaseExecutionManager abstract contract.
"""

from __future__ import annotations

from app.core.models import ComponentHealth, SystemHealthStatus
from app.orchestrator.base import (
    BaseExecutionManager,
    ExecutionRoutingError,
    OrchestratorInitializationError,
)
from app.orchestrator.models import (
    ExecutionRoute,
    OrchestratorContext,
    OrchestratorResponse,
)


class ExecutionManager:
    """Service facade coordinating downstream service execution via resolved ExecutionRoute.

    Responsibility:
        Accepts an ExecutionRoute and OrchestratorContext, delegates execution to an injected
        BaseExecutionManager provider, translates execution failures into domain errors,
        and manages operational lifecycle health.

    Design Notes:
        ExecutionManager deliberately avoids direct imports of AgentService, RAGService,
        NavigationService, or BrowserService. All downstream coordination is abstracted
        through the BaseExecutionManager interface to maintain clean dependency boundaries.
    """

    def __init__(self, manager: BaseExecutionManager) -> None:
        """Initialize ExecutionManager with an injected BaseExecutionManager dependency.

        Args:
            manager: Injected BaseExecutionManager implementation responsible for
                     coordinating downstream service execution.
        """
        self._manager = manager
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the execution manager service has been initialized.

        Raises:
            OrchestratorInitializationError: If initialize() has not been called.
        """
        if not self._initialized:
            raise OrchestratorInitializationError(
                "ExecutionManager is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize execution manager and underlying provider runtime state. Idempotent."""
        if self._initialized:
            return

        if hasattr(self._manager, "initialize"):
            await self._manager.initialize()

        self._initialized = True

    async def close(self) -> None:
        """Close execution manager and release provider resources."""
        if hasattr(self._manager, "close"):
            await self._manager.close()

        self._initialized = False

    async def execute(
        self,
        route: ExecutionRoute,
        context: OrchestratorContext,
    ) -> OrchestratorResponse:
        """Validate inputs and execute a resolved ExecutionRoute via injected manager provider.

        Args:
            route: ExecutionRoute model resolved from intent classification and routing.
            context: Active OrchestratorContext model snapshot for this request.

        Returns:
            OrchestratorResponse: Final orchestration response from downstream service execution.

        Raises:
            OrchestratorInitializationError: If service is uninitialized.
            ExecutionRoutingError: If route or context parameters are invalid or execution fails.
        """
        self._require_initialized()
        if not isinstance(route, ExecutionRoute):
            raise ExecutionRoutingError("Invalid ExecutionRoute instance provided.")
        if not isinstance(context, OrchestratorContext):
            raise ExecutionRoutingError("Invalid OrchestratorContext instance provided.")
        if not route.services:
            raise ExecutionRoutingError("ExecutionRoute services tuple cannot be empty.")

        try:
            return await self._manager.execute(route, context)
        except ExecutionRoutingError:
            raise
        except Exception as e:
            raise ExecutionRoutingError(
                f"Downstream execution failed for route '{route.route_id}' "
                f"with services {list(route.services)}: {str(e)}"
            ) from e

    async def health_check(self) -> ComponentHealth:
        """Check operational health of the execution manager service.

        Returns:
            ComponentHealth: Operational component health status model.
        """
        if not self._initialized:
            return ComponentHealth(
                component_name="execution_manager",
                status=SystemHealthStatus.UNHEALTHY,
                message="ExecutionManager uninitialized.",
            )

        manager_healthy = True
        if hasattr(self._manager, "health_check"):
            res = await self._manager.health_check()
            if isinstance(res, ComponentHealth):
                manager_healthy = res.status == SystemHealthStatus.HEALTHY
            elif isinstance(res, bool):
                manager_healthy = res

        return ComponentHealth(
            component_name="execution_manager",
            status=SystemHealthStatus.HEALTHY if manager_healthy else SystemHealthStatus.UNHEALTHY,
            message="ExecutionManager operational."
            if manager_healthy
            else "ExecutionManager provider degraded.",
        )
