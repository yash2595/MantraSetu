"""Orchestrator Application Service Facade for MantraSetu AgentOS.

This module implements OrchestratorService as the main application facade for the Orchestrator
subsystem, coordinating intent detection, execution routing, downstream service execution,
and context persistence via injected subsystem dependencies.
"""

from __future__ import annotations

from uuid import UUID

from app.core.models import ComponentHealth, SystemHealthStatus
from app.orchestrator.base import (
    OrchestrationExecutionError,
    OrchestratorError,
    OrchestratorInitializationError,
)
from app.orchestrator.executor import ExecutionManager
from app.orchestrator.intent import IntentDetectionService
from app.orchestrator.models import (
    OrchestratorContext,
    OrchestratorResponse,
    UserRequest,
)
from app.orchestrator.router import RouterService
from app.orchestrator.store import OrchestratorStore


class OrchestratorService:
    """Application facade service coordinating the complete Orchestrator subsystem pipeline.

    Responsibility:
        Accepts UserRequest models, creates OrchestratorContext snapshots, classifies user
        intent, resolves execution routes, delegates downstream execution, persists enriched
        context via OrchestratorStore, and returns OrchestratorResponse without LLM SDK
        or browser execution dependencies.

    Pipeline:
        UserRequest
            → Create OrchestratorContext
            → IntentDetectionService.detect()
            → RouterService.route()
            → ExecutionManager.execute()
            → OrchestratorStore.save()
            → OrchestratorResponse
    """

    def __init__(
        self,
        intent_service: IntentDetectionService,
        router_service: RouterService,
        execution_manager: ExecutionManager,
        store: OrchestratorStore,
    ) -> None:
        """Initialize OrchestratorService with strictly injected subsystem dependencies.

        Args:
            intent_service: Injected IntentDetectionService instance.
            router_service: Injected RouterService instance.
            execution_manager: Injected ExecutionManager instance for downstream coordination.
            store: Injected OrchestratorStore instance for context persistence.
        """
        self._intent_service = intent_service
        self._router_service = router_service
        self._execution_manager = execution_manager
        self._store = store
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the orchestrator service has been initialized.

        Raises:
            OrchestratorInitializationError: If initialize() has not been called.
        """
        if not self._initialized:
            raise OrchestratorInitializationError(
                "OrchestratorService is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize orchestrator service and all underlying subsystem dependencies. Idempotent."""
        if self._initialized:
            return

        await self._store.initialize()
        await self._intent_service.initialize()
        await self._router_service.initialize()
        await self._execution_manager.initialize()

        self._initialized = True

    async def close(self) -> None:
        """Close orchestrator service and release all subsystem resources in reverse order."""
        await self._execution_manager.close()
        await self._router_service.close()
        await self._intent_service.close()
        await self._store.close()

        self._initialized = False

    async def process(self, request: UserRequest) -> OrchestratorResponse:
        """Execute the full orchestration pipeline for an incoming UserRequest.

        Pipeline Stages:
            1. Validate UserRequest.
            2. Create base OrchestratorContext.
            3. Detect user intent via IntentDetectionService.
            4. Resolve execution route via RouterService.
            5. Execute resolved route via ExecutionManager.
            6. Persist enriched OrchestratorContext via OrchestratorStore.
            7. Return OrchestratorResponse from downstream execution.

        Args:
            request: Incoming UserRequest model to orchestrate.

        Returns:
            OrchestratorResponse: Final orchestration response model.

        Raises:
            OrchestratorInitializationError: If service is uninitialized.
            OrchestratorError: If request is invalid or any pipeline stage fails.
        """
        self._require_initialized()
        if not isinstance(request, UserRequest):
            raise OrchestratorError("Invalid UserRequest instance provided.")
        if not request.user_input or not request.user_input.strip():
            raise OrchestratorError("UserRequest user_input string cannot be empty or blank.")

        try:
            # Stage 1: Create base context
            context = OrchestratorContext(
                request_id=request.request_id,
                session_id=request.session_id,
            )

            # Stage 2: Detect intent
            detected_intent = await self._intent_service.detect(request)

            # Stage 3: Enrich context with detected intent
            context = OrchestratorContext(
                request_id=request.request_id,
                session_id=request.session_id,
                detected_intent=detected_intent,
            )

            # Stage 4: Resolve execution route
            route = await self._router_service.route(detected_intent, context)

            # Stage 5: Enrich context with resolved route
            final_context = OrchestratorContext(
                request_id=request.request_id,
                session_id=request.session_id,
                detected_intent=detected_intent,
                route=route,
                metadata={
                    "user_input": request.user_input,
                    "intent_type": detected_intent.intent_type.value,
                    "confidence": detected_intent.confidence,
                    "services": list(route.services),
                },
            )

            # Stage 6: Execute resolved route via downstream manager
            response = await self._execution_manager.execute(route, final_context)

            # Stage 7: Persist final context
            await self._store.save(final_context)

            return response

        except OrchestratorError:
            raise
        except Exception as e:
            raise OrchestrationExecutionError(
                f"Orchestration pipeline failed for request '{request.request_id}': {str(e)}"
            ) from e

    async def get_context(self, request_id: UUID) -> OrchestratorContext:
        """Retrieve the persisted OrchestratorContext for a processed request.

        Args:
            request_id: Associated UserRequest identifier UUID.

        Returns:
            OrchestratorContext: Retrieved orchestrator context model.

        Raises:
            OrchestratorInitializationError: If service is uninitialized.
            OrchestratorError: If request_id is invalid or context not found.
        """
        self._require_initialized()
        if not isinstance(request_id, UUID):
            raise OrchestratorError("Invalid request_id UUID provided.")

        try:
            return await self._store.get(request_id)
        except OrchestratorError:
            raise
        except Exception as e:
            raise OrchestratorError(
                f"Failed to retrieve OrchestratorContext for request '{request_id}': {str(e)}"
            ) from e

    async def health_check(self) -> ComponentHealth:
        """Check aggregated operational health across all Orchestrator subsystem services.

        Returns:
            ComponentHealth: Aggregated component health status model.
        """
        if not self._initialized:
            return ComponentHealth(
                component_name="orchestrator_service",
                status=SystemHealthStatus.UNHEALTHY,
                message="OrchestratorService uninitialized.",
            )

        store_health = await self._store.health_check()
        intent_health = await self._intent_service.health_check()
        router_health = await self._router_service.health_check()
        exec_health = await self._execution_manager.health_check()

        is_healthy = all(
            isinstance(h, ComponentHealth) and h.status == SystemHealthStatus.HEALTHY
            for h in (store_health, intent_health, router_health, exec_health)
        )

        return ComponentHealth(
            component_name="orchestrator_service",
            status=SystemHealthStatus.HEALTHY if is_healthy else SystemHealthStatus.UNHEALTHY,
            message="OrchestratorService operational."
            if is_healthy
            else "OrchestratorService subsystem component degraded.",
        )
