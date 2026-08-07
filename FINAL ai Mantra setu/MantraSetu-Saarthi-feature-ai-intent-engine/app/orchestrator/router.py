"""Router Service orchestration layer for MantraSetu AgentOS.

This module implements RouterService, coordinating intent-to-service execution route resolution
with an injected BaseRouter provider without LLM SDK or browser dependencies.
"""

from __future__ import annotations

from app.core.models import ComponentHealth, SystemHealthStatus
from app.orchestrator.base import (
    BaseRouter,
    OrchestratorInitializationError,
    RoutingError,
)
from app.orchestrator.models import (
    DetectedIntent,
    ExecutionRoute,
    OrchestratorContext,
)


class RouterService:
    """Service facade coordinating intent-to-service execution routing resolution.

    Responsibility:
        Validates DetectedIntent and OrchestratorContext models, delegates route resolution
        to an injected BaseRouter provider, translates routing errors into domain exceptions,
        and manages operational lifecycle health.
    """

    def __init__(self, router: BaseRouter) -> None:
        """Initialize RouterService with an injected BaseRouter dependency.

        Args:
            router: Injected BaseRouter implementation.
        """
        self._router = router
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the router service has been initialized.

        Raises:
            OrchestratorInitializationError: If initialize() has not been called.
        """
        if not self._initialized:
            raise OrchestratorInitializationError(
                "RouterService is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize router service and underlying provider runtime state. Idempotent."""
        if self._initialized:
            return

        if hasattr(self._router, "initialize"):
            await self._router.initialize()

        self._initialized = True

    async def close(self) -> None:
        """Close router service and release provider resources."""
        if hasattr(self._router, "close"):
            await self._router.close()

        self._initialized = False

    async def route(
        self,
        intent: DetectedIntent,
        context: OrchestratorContext,
    ) -> ExecutionRoute:
        """Validate inputs and resolve the execution service route via injected router provider.

        Args:
            intent: DetectedIntent model from intent classification stage.
            context: Active OrchestratorContext model snapshot.

        Returns:
            ExecutionRoute: Resolved execution service routing plan model.

        Raises:
            OrchestratorInitializationError: If service is uninitialized.
            RoutingError: If intent or context parameters are invalid or route resolution fails.
        """
        self._require_initialized()
        if not isinstance(intent, DetectedIntent):
            raise RoutingError("Invalid DetectedIntent instance provided.")
        if not isinstance(context, OrchestratorContext):
            raise RoutingError("Invalid OrchestratorContext instance provided.")

        try:
            return await self._router.route(intent, context)
        except RoutingError:
            raise
        except Exception as e:
            raise RoutingError(
                f"Execution route resolution failed for intent '{intent.intent_type}': {str(e)}"
            ) from e

    async def health_check(self) -> ComponentHealth:
        """Check operational health of the router service.

        Returns:
            ComponentHealth: Operational component health status model.
        """
        if not self._initialized:
            return ComponentHealth(
                component_name="router_service",
                status=SystemHealthStatus.UNHEALTHY,
                message="RouterService uninitialized.",
            )

        router_healthy = True
        if hasattr(self._router, "health_check"):
            res = await self._router.health_check()
            if isinstance(res, ComponentHealth):
                router_healthy = res.status == SystemHealthStatus.HEALTHY
            elif isinstance(res, bool):
                router_healthy = res

        return ComponentHealth(
            component_name="router_service",
            status=SystemHealthStatus.HEALTHY if router_healthy else SystemHealthStatus.UNHEALTHY,
            message="RouterService operational."
            if router_healthy
            else "RouterService provider degraded.",
        )
