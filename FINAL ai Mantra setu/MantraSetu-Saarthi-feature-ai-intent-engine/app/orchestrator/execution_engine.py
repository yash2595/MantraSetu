"""Concrete Execution Engine for the Orchestrator subsystem in MantraSetu AgentOS.

This module implements OrchestratorExecutionEngine, the concrete BaseExecutionManager
implementation that resolves service names from an ExecutionRoute and dispatches execution
to registered injectable service handlers via a handler registry pattern.
"""

from __future__ import annotations

from typing import Awaitable, Callable

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

# Type alias for injectable service handler callables.
# Each handler accepts an OrchestratorContext and returns an OrchestratorResponse.
ServiceHandler = Callable[[OrchestratorContext], Awaitable[OrchestratorResponse]]


class OrchestratorExecutionEngine(BaseExecutionManager):
    """Concrete execution engine that dispatches to registered service handlers by route name.

    Responsibility:
        Iterates the service names in an ExecutionRoute, resolves each name against an internal
        handler registry, invokes the first matched handler with the active OrchestratorContext,
        and returns the resulting OrchestratorResponse.

    Design Notes:
        - Downstream services (AgentService, RAGService, NavigationService, BrowserService)
          are never imported directly. Each is registered as an async callable handler at
          composition time, preserving clean dependency boundaries.
        - The engine executes the first resolvable service in route.services. This intentional
          priority ordering means routes should list services in execution precedence order.
        - If no registered handler matches any service in the route, ExecutionRoutingError
          is raised with a descriptive diagnostic message.

    Handler Registration:
        Use register_handler() to bind a service name string to an async handler callable
        before calling initialize().

        Example:
            engine = OrchestratorExecutionEngine()
            engine.register_handler('agent_service', agent_handler)
            engine.register_handler('rag_service', rag_handler)
    """

    def __init__(self) -> None:
        """Initialize OrchestratorExecutionEngine with an empty service handler registry."""
        self._handlers: dict[str, ServiceHandler] = {}
        self._initialized = False

    def register_handler(self, service_name: str, handler: ServiceHandler) -> None:
        """Register an async callable handler for a given service name.

        Must be called before initialize(). Registering the same service_name twice
        will silently overwrite the previous handler.

        Args:
            service_name: Service name string matching entries in ExecutionRoute.services.
            handler: Async callable accepting OrchestratorContext and returning OrchestratorResponse.

        Raises:
            TypeError: If service_name is not a non-empty string or handler is not callable.
        """
        if not isinstance(service_name, str) or not service_name.strip():
            raise TypeError("service_name must be a non-empty string.")
        if not callable(handler):
            raise TypeError("handler must be an async callable.")
        self._handlers[service_name.strip()] = handler

    def _require_initialized(self) -> None:
        """Verify that the execution engine has been initialized.

        Raises:
            OrchestratorInitializationError: If initialize() has not been called.
        """
        if not self._initialized:
            raise OrchestratorInitializationError(
                "OrchestratorExecutionEngine is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize execution engine runtime state. Idempotent."""
        if self._initialized:
            return
        self._initialized = True

    async def close(self) -> None:
        """Close execution engine and clear the handler registry."""
        self._handlers.clear()
        self._initialized = False

    async def execute(
        self,
        route: ExecutionRoute,
        context: OrchestratorContext,
    ) -> OrchestratorResponse:
        """Resolve and dispatch execution to the first matching registered service handler.

        Iterates route.services in order, resolves each against the handler registry,
        and invokes the first matched handler. Raises ExecutionRoutingError if no registered
        handler matches any service name in the route.

        Args:
            route: ExecutionRoute model whose services tuple defines execution precedence.
            context: Active OrchestratorContext model snapshot for this request.

        Returns:
            OrchestratorResponse: Response returned by the resolved service handler.

        Raises:
            OrchestratorInitializationError: If engine is uninitialized.
            ExecutionRoutingError: If inputs are invalid, no services are defined,
                                   or no registered handler matches any route service.
        """
        self._require_initialized()
        if not isinstance(route, ExecutionRoute):
            raise ExecutionRoutingError("Invalid ExecutionRoute instance provided.")
        if not isinstance(context, OrchestratorContext):
            raise ExecutionRoutingError("Invalid OrchestratorContext instance provided.")
        if not route.services:
            raise ExecutionRoutingError("ExecutionRoute services tuple cannot be empty.")

        # Resolve first matching handler in route service priority order
        for service_name in route.services:
            handler = self._handlers.get(service_name)
            if handler is not None:
                try:
                    return await handler(context)
                except ExecutionRoutingError:
                    raise
                except Exception as e:
                    raise ExecutionRoutingError(
                        f"Service handler '{service_name}' failed for request "
                        f"'{context.request_id}': {str(e)}"
                    ) from e

        # No handler matched any service in the route
        raise ExecutionRoutingError(
            f"No registered handler found for any service in route "
            f"{list(route.services)}. Register handlers via register_handler()."
        )

    async def health_check(self) -> ComponentHealth:
        """Check operational health of the execution engine.

        Returns:
            ComponentHealth: Operational component health status model.
        """
        return ComponentHealth(
            component_name="orchestrator_execution_engine",
            status=SystemHealthStatus.HEALTHY if self._initialized else SystemHealthStatus.UNHEALTHY,
            message=f"OrchestratorExecutionEngine operational "
                    f"with {len(self._handlers)} registered handler(s)."
            if self._initialized
            else "OrchestratorExecutionEngine uninitialized.",
        )
