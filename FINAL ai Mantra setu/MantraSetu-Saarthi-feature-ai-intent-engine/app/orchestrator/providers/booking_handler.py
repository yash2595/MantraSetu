"""Booking execution handler for the Orchestrator subsystem."""

import logging
from uuid import uuid4

from app.agent.base import AgentError, AgentExecutionError
from app.agent.models import AgentTask
from app.agent.service import AgentService
from app.orchestrator.base import OrchestrationExecutionError
from app.orchestrator.models import OrchestratorContext, OrchestratorResponse

logger = logging.getLogger(__name__)


class BookingHandler:
    """Execution engine handler for BOOKING_TASK intents.

    Compatible with the OrchestratorExecutionEngine handler registry.
    """

    def __init__(self, agent_service: AgentService) -> None:
        """Initialize the Booking execution handler.

        Args:
            agent_service: Initialized AgentService instance.
        """
        if agent_service is None:
            raise ValueError("AgentService dependency cannot be None.")
        self._agent = agent_service
        logger.info("BookingHandler initialized")

    async def __call__(self, context: OrchestratorContext) -> OrchestratorResponse:
        """Handle execution of a BOOKING_TASK intent route.

        Args:
            context: Active OrchestratorContext model snapshot.

        Returns:
            OrchestratorResponse: Final orchestrated response model.

        Raises:
            OrchestrationExecutionError: If booking agent fails or input is missing.
        """
        # 1. Extract booking request
        user_input = context.metadata.get("user_input")
        if not user_input or not isinstance(user_input, str):
            logger.error("Missing user_input in OrchestratorContext metadata.")
            raise OrchestrationExecutionError(
                "Cannot execute BOOKING_TASK route: missing user_input in context."
            )

        logger.debug(
            "Executing booking pipeline [request_id=%s, input='%s']",
            context.request_id,
            user_input,
        )

        # Build intent string if available
        intent_type_str = None
        if context.detected_intent:
            intent_type_str = context.detected_intent.intent_type.value

        # Construct autonomous task unit
        task = AgentTask(
            task_id=uuid4(),
            user_input=user_input,
            intent=intent_type_str,
        )

        # 2. Call existing AgentService abstraction
        try:
            # AgentService plans and executes required workflow
            result = await self._agent.run(
                task=task,
                conversation_id=None,
                session_id=context.session_id,
            )
        except (AgentError, AgentExecutionError) as exc:
            logger.error("AgentService failed during execution: %s", exc)
            raise OrchestrationExecutionError("Booking execution failed.") from exc
        except Exception as exc:
            logger.exception("Unexpected error during booking execution.")
            raise OrchestrationExecutionError(
                "Unexpected error occurred during booking pipeline."
            ) from exc

        # 3. Convert result into OrchestratorResponse
        logger.info(
            "Booking execution completed [request_id=%s, success=%s, actions=%d]",
            context.request_id,
            result.success,
            len(result.actions),
        )

        return OrchestratorResponse(
            request_id=context.request_id,
            success=result.success,
            response=result.output.strip() if result.output else "Booking task executed.",
            metadata={
                "provider": "booking_handler",
                "execution_id": str(result.execution_id),
                "actions_taken": len(result.actions),
            },
        )
