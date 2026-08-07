"""Intent Detection Service orchestration layer for MantraSetu AgentOS.

This module implements IntentDetectionService, coordinating user request intent classification
with an injected BaseIntentDetector provider without LLM SDK or browser dependencies.
"""

from __future__ import annotations

from app.core.models import ComponentHealth, SystemHealthStatus
from app.orchestrator.base import (
    BaseIntentDetector,
    IntentDetectionError,
    OrchestratorInitializationError,
)
from app.orchestrator.models import DetectedIntent, UserRequest


class IntentDetectionService:
    """Service facade coordinating user intent classification requests.

    Responsibility:
        Validates UserRequest models, delegates intent classification to an injected
        BaseIntentDetector provider, translates detection errors into domain exceptions,
        and manages operational lifecycle health.
    """

    def __init__(self, detector: BaseIntentDetector) -> None:
        """Initialize IntentDetectionService with an injected BaseIntentDetector dependency.

        Args:
            detector: Injected BaseIntentDetector implementation.
        """
        self._detector = detector
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the intent detection service has been initialized.

        Raises:
            OrchestratorInitializationError: If initialize() has not been called.
        """
        if not self._initialized:
            raise OrchestratorInitializationError(
                "IntentDetectionService is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize intent detection service and underlying provider runtime state. Idempotent."""
        if self._initialized:
            return

        if hasattr(self._detector, "initialize"):
            await self._detector.initialize()

        self._initialized = True

    async def close(self) -> None:
        """Close intent detection service and release provider resources."""
        if hasattr(self._detector, "close"):
            await self._detector.close()

        self._initialized = False

    async def detect(self, request: UserRequest) -> DetectedIntent:
        """Validate UserRequest and classify user intent via injected detector provider.

        Args:
            request: Incoming UserRequest model to classify.

        Returns:
            DetectedIntent: Classified intent model with type, confidence, and entities.

        Raises:
            OrchestratorInitializationError: If service is uninitialized.
            IntentDetectionError: If request is invalid or intent detection fails.
        """
        self._require_initialized()
        if not isinstance(request, UserRequest):
            raise IntentDetectionError("Invalid UserRequest instance provided.")
        if not request.user_input or not request.user_input.strip():
            raise IntentDetectionError("UserRequest user_input string cannot be empty or blank.")

        try:
            return await self._detector.detect(request)
        except IntentDetectionError:
            raise
        except Exception as e:
            raise IntentDetectionError(
                f"Intent detection failed for request '{request.request_id}': {str(e)}"
            ) from e

    async def health_check(self) -> ComponentHealth:
        """Check operational health of the intent detection service.

        Returns:
            ComponentHealth: Operational component health status model.
        """
        if not self._initialized:
            return ComponentHealth(
                component_name="intent_detection_service",
                status=SystemHealthStatus.UNHEALTHY,
                message="IntentDetectionService uninitialized.",
            )

        detector_healthy = True
        if hasattr(self._detector, "health_check"):
            res = await self._detector.health_check()
            if isinstance(res, ComponentHealth):
                detector_healthy = res.status == SystemHealthStatus.HEALTHY
            elif isinstance(res, bool):
                detector_healthy = res

        return ComponentHealth(
            component_name="intent_detection_service",
            status=SystemHealthStatus.HEALTHY if detector_healthy else SystemHealthStatus.UNHEALTHY,
            message="IntentDetectionService operational."
            if detector_healthy
            else "IntentDetectionService provider degraded.",
        )
