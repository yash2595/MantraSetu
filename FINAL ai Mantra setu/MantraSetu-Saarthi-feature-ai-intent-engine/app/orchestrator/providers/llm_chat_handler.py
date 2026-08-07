"""LLM chat execution handler for the Orchestrator subsystem."""

import logging

from app.core.exceptions import ApplicationError
from app.llm.models import LLMRequest
from app.orchestrator.base import OrchestrationExecutionError
from app.orchestrator.models import OrchestratorContext, OrchestratorResponse
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)


class LLMChatHandler:
    """Execution engine handler for generating conversational responses via LLM.

    Compatible with the OrchestratorExecutionEngine handler registry.
    """

    def __init__(self, ai_service: AIService) -> None:
        """Initialize the LLM chat handler.

        Args:
            ai_service: Initialized AIService instance to communicate with LLM providers.
        """
        if ai_service is None:
            raise ValueError("AIService dependency cannot be None.")
        self._ai = ai_service
        logger.info("LLMChatHandler initialized")

    async def __call__(self, context: OrchestratorContext) -> OrchestratorResponse:
        """Handle execution of a CHAT intent route.

        Args:
            context: Active OrchestratorContext model snapshot.

        Returns:
            OrchestratorResponse: Final orchestrated response model.

        Raises:
            OrchestrationExecutionError: If AI generation fails or input is unresolvable.
        """
        # 1. Extract user input
        user_input = context.metadata.get("user_input")
        if not user_input or not isinstance(user_input, str):
            logger.error("Missing or invalid user_input in OrchestratorContext metadata.")
            raise OrchestrationExecutionError(
                "Cannot execute CHAT route: missing user_input in context."
            )

        # 2. Extract session context
        session_id_str = str(context.session_id) if context.session_id else None

        # 3. Create LLM request
        logger.debug(
            "Generating CHAT response [request_id=%s, session_id=%s]",
            context.request_id,
            session_id_str,
        )
        
        llm_req = LLMRequest(
            prompt=user_input,
            conversation_id=session_id_str,
            temperature=0.7,  # Conversational temperature
        )

        # 4. Call existing AIService abstraction
        try:
            response = await self._ai.generate(request=llm_req)
        except ApplicationError as exc:
            logger.error("AI Service failed during CHAT execution: %s", exc)
            raise OrchestrationExecutionError(
                f"LLM generation failed: {str(exc)}"
            ) from exc
        except Exception as exc:
            logger.exception("Unexpected error during CHAT execution.")
            raise OrchestrationExecutionError(
                "Unexpected error occurred during conversational generation."
            ) from exc

        # 5. Return structured response
        logger.info(
            "CHAT execution completed [request_id=%s, response_len=%d]",
            context.request_id,
            len(response.content),
        )

        intent_value = "unknown"
        if context.detected_intent:
            intent_value = context.detected_intent.intent_type.value

        return OrchestratorResponse(
            request_id=context.request_id,
            success=True,
            response=response.content.strip(),
            metadata={
                "provider": "llm_chat_handler",
                "model": response.metadata.get("model", "unknown"),
                "intent": intent_value,
                "original_input": user_input,
            },
        )
