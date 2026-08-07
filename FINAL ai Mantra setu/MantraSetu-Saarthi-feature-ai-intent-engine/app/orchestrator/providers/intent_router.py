"""Intent-based routing provider for the Orchestrator subsystem."""

import logging
from uuid import uuid4

from app.orchestrator.base import BaseRouter, RoutingError
from app.orchestrator.models import (
    DetectedIntent,
    ExecutionRoute,
    IntentType,
    OrchestratorContext,
)

logger = logging.getLogger(__name__)


class IntentRouter(BaseRouter):
    """Static rule-based implementation of BaseRouter.

    Resolves service execution routes based on detected IntentType.
    """

    def __init__(self) -> None:
        """Initialize the IntentRouter."""
        # Immutable mapping of IntentType to a tuple of required service identifiers.
        self._routing_table: dict[IntentType, tuple[str, ...]] = {
            IntentType.CHAT: ("llm_service",),
            IntentType.INFORMATION_QUERY: ("rag_service",),
            IntentType.NAVIGATION_TASK: ("navigation_service", "browser_service"),
            IntentType.BOOKING_TASK: ("agent_service", "browser_service"),
            IntentType.SPIRITUAL_SERVICE: ("agent_service", "rag_service"),
            IntentType.UNKNOWN: ("llm_service",),
        }
        logger.info("IntentRouter initialized")

    async def route(
        self,
        intent: DetectedIntent,
        context: OrchestratorContext,
    ) -> ExecutionRoute:
        """Resolve the execution service route for a detected intent.

        Args:
            intent: DetectedIntent model from intent classification.
            context: Active OrchestratorContext model snapshot.

        Returns:
            ExecutionRoute: Resolved execution service routing plan model.

        Raises:
            RoutingError: If intent is invalid or routing resolution fails.
        """
        if intent is None:
            raise RoutingError("DetectedIntent cannot be None for routing.")
        if context is None:
            raise RoutingError("OrchestratorContext cannot be None for routing.")

        intent_type = intent.intent_type
        
        # Guard against completely unrecognized Enum values
        if not isinstance(intent_type, IntentType):
            logger.warning(
                "Invalid or unsupported intent type encountered: %s. Defaulting to UNKNOWN.",
                type(intent_type),
            )
            intent_type = IntentType.UNKNOWN

        # Resolve services from routing table
        services = self._routing_table.get(intent_type)

        # Fallback if somehow missing from the mapping table
        if services is None:
            logger.warning(
                "No route mapping found for intent: %s. Defaulting to UNKNOWN route.",
                intent_type.value,
            )
            services = self._routing_table[IntentType.UNKNOWN]

        logger.info(
            "Resolved route for intent '%s' -> services: %s [context_request_id=%s]",
            intent_type.value,
            list(services),
            context.request_id,
        )

        return ExecutionRoute(
            route_id=uuid4(),
            intent=intent_type,
            services=services,
        )
