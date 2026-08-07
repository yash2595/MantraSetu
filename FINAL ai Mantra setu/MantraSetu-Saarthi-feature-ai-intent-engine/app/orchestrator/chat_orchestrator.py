"""Backward-compatibility adapter for legacy Chat API routes.

ChatOrchestrator acts strictly as a thin compatibility adapter delegating requests
to AIOrchestrator. It contains zero orchestration, execution, or business logic.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from app.orchestrator.ai_orchestrator import AIOrchestrator
from app.orchestrator.context import OrchestratorDependencies
from app.orchestrator.pipeline import DEFAULT_PIPELINE, OrchestrationPipeline
from app.schemas.chat import AIResponse, ChatRequest, ChatResponse
from app.schemas.interaction import InteractionRequest, InteractionResponse

logger = logging.getLogger(__name__)


from app.orchestrator.builder import AIOrchestratorBuilder


class ChatOrchestrator:
    """Thin compatibility adapter wrapping AIOrchestrator for legacy endpoints."""

    def __init__(
        self,
        dependencies: OrchestratorDependencies,
        pipeline: OrchestrationPipeline | None = None,
        ai_orchestrator: AIOrchestrator | None = None,
    ) -> None:
        self._dependencies = dependencies
        self._pipeline = pipeline or DEFAULT_PIPELINE
        self._ai_orchestrator = ai_orchestrator or AIOrchestrator()

    @property
    def pipeline(self) -> OrchestrationPipeline:
        """Expose the orchestration pipeline metadata."""
        return self._pipeline

    @property
    def ai_orchestrator(self) -> AIOrchestrator:
        """Expose the underlying AIOrchestrator instance."""
        return self._ai_orchestrator

    async def handle(self, request: ChatRequest) -> AIResponse:
        """Adapt ChatRequest to InteractionRequest, delegate to AIOrchestrator, return AIResponse."""
        metadata = dict(request.metadata or {})
        session_id = str(metadata.get("session_id") or request.conversation_id or "anonymous_session")
        request_id = metadata.get("request_id") or uuid4()

        from app.orchestrator.orchestrator_models import OrchestratorRequest

        orchestrator_request = OrchestratorRequest(
            user_message=request.message,
            session_id=session_id,
            conversation_id=request.conversation_id or "default_conv",
            request_id=request_id if isinstance(request_id, str) else request_id.hex if hasattr(request_id, "hex") else str(request_id),
            user_parameters=metadata,
        )

        orchestrator_response = await self._ai_orchestrator.process_request(orchestrator_request)

        return self._adapt_to_ai_response(orchestrator_response)

    def _adapt_to_ai_response(self, response: Any) -> AIResponse:
        """Convert normalized response into legacy AIResponse payload."""
        content = getattr(response, "text", None) or getattr(response, "content", None)
        if not isinstance(content, str) or not content:
            content = "MantraSetu AI could not process this request right now."

        finish_reason = getattr(response, "finish_reason", None)
        if not isinstance(finish_reason, str):
            finish_reason = "stop" if getattr(response, "success", True) else "error"

        metadata = getattr(response, "metadata", None)
        meta_dict = dict(metadata.__dict__) if hasattr(metadata, "__dict__") else dict(metadata) if isinstance(metadata, dict) else {}

        provider = meta_dict.get("provider")
        provider_str = str(provider) if isinstance(provider, str) else None

        model = meta_dict.get("model")
        model_str = str(model) if isinstance(model, str) else None

        intent_obj = getattr(response, "intent", None)
        intent_name = getattr(intent_obj, "name", "general_chat") if intent_obj else getattr(response, "response_type", "general_chat")
        intent_str = str(intent_name) if isinstance(intent_name, str) else "general_chat"

        confidence = getattr(intent_obj, "confidence", 0.0) if intent_obj else 0.0
        conf_float = float(confidence) if isinstance(confidence, (int, float)) else 0.0

        exec_time = getattr(response, "execution_time_ms", 0.0) or meta_dict.get("latency_ms", 0.0)
        exec_time_float = float(exec_time) if isinstance(exec_time, (int, float)) else 0.0

        return AIResponse(
            content=content,
            provider=provider_str,
            model=model_str,
            finish_reason=finish_reason,
            metadata={
                "intent": intent_str,
                "confidence": conf_float,
                "pipeline": self._pipeline.name,
                "execution_time_ms": exec_time_float,
                **meta_dict,
            },
        )
