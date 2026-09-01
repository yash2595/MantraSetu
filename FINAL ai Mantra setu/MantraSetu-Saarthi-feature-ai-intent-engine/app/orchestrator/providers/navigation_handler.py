"""Navigation execution handler for the Orchestrator subsystem."""

import logging

from app.navigation.base import NavigationError
from app.navigation.models import NavigationContext
from app.navigation.service import NavigationService
from app.orchestrator.base import OrchestrationExecutionError
from app.orchestrator.models import OrchestratorContext, OrchestratorResponse

logger = logging.getLogger(__name__)


class NavigationHandler:
    """Execution engine handler for NAVIGATION_TASK intents.

    Compatible with the OrchestratorExecutionEngine handler registry.
    """

    def __init__(self, navigation_service: NavigationService) -> None:
        """Initialize the Navigation execution handler.

        Args:
            navigation_service: Initialized NavigationService instance.
        """
        if navigation_service is None:
            raise ValueError("NavigationService dependency cannot be None.")
        self._nav = navigation_service
        logger.info("NavigationHandler initialized")

    async def __call__(self, context: OrchestratorContext) -> OrchestratorResponse:
        """Handle execution of a NAVIGATION_TASK intent route.

        Args:
            context: Active OrchestratorContext model snapshot.

        Returns:
            OrchestratorResponse: Final orchestrated response model.

        Raises:
            OrchestrationExecutionError: If navigation fails or input is missing.
        """
        # 1. Extract navigation request
        user_input = context.metadata.get("user_input")
        if not user_input or not isinstance(user_input, str):
            logger.error("Missing user_input in OrchestratorContext metadata.")
            raise OrchestrationExecutionError(
                "Cannot execute NAVIGATION_TASK route: missing user_input in context."
            )

        logger.debug(
            "Executing navigation pipeline [request_id=%s, goal='%s']",
            context.request_id,
            user_input,
        )

        # Build a temporary navigation context tracking state
        nav_context = NavigationContext(
            session_id=context.session_id,
            current_url=None,
        )

        # 2. Call existing NavigationService abstraction
        try:
            # Generate the navigation plan
            plan = await self._nav.create_plan(goal=user_input, context=nav_context)

        except NavigationError as exc:
            logger.error("NavigationService failed during execution: %s", exc)
            raise OrchestrationExecutionError("Navigation execution failed.") from exc
        except Exception as exc:
            logger.exception("Unexpected error during navigation execution.")
            raise OrchestrationExecutionError("Unexpected error occurred during navigation pipeline.") from exc

        # 3. Convert result into OrchestratorResponse
        import json
        steps_count = len(plan.steps) if plan and getattr(plan, "steps", None) else 0
        response_data = {
            "action": "NAVIGATE",
            "target": getattr(plan, "final_url", "/") if hasattr(plan, "final_url") else "/",
            "intent": "NAVIGATE",
            "active_field": None,
            "value": None,
            "confidence": 0.95,
            "response_text": "I have initiated the navigation process to assist with your request."
        }
        response_text = json.dumps(response_data)

        logger.info(
            "Navigation execution completed [request_id=%s, plan_id=%s, steps=%d]",
            context.request_id,
            getattr(plan, "plan_id", "unknown"),
            steps_count,
        )

        return OrchestratorResponse(
            request_id=context.request_id,
            success=True,
            response=response_text,
            metadata={
                "provider": "navigation_handler",
                "plan_id": str(getattr(plan, "plan_id", "")),
                "steps_count": steps_count,
            },
        )
