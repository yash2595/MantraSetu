"""Null Object pattern implementations for optional orchestrator dependencies.

Null Objects satisfy collaborator interface contracts when optional dependencies are
unsupplied, eliminating runtime hasattr() and None checks during pipeline execution.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.interfaces.chat_orchestrator import (
    IContextManager,
    IExecutionEngine,
    IIntentEngine,
    IPlanner,
    IResponseFormatter,
    ISessionManager,
)
from app.schemas.api.interaction import InteractionRequest, InteractionResponse
from app.schemas.chat import AIResponse, ChatRequest
from app.schemas.context import ConversationContext
from app.schemas.domain.interaction import (
    ExecutionResult,
    IntentResult,
    PipelineResult,
    PipelineResultStatus,
    Plan,
)


class NoopSessionManager(ISessionManager):
    """Null Object session manager returning empty session data."""

    async def load_session(self, session_id: str, **kwargs: Any) -> dict[str, Any]:
        return {}

    async def save_session(self, session_id: str, session_data: dict[str, Any], **kwargs: Any) -> None:
        pass


class NoopContextManager(IContextManager):
    """Null Object context manager returning request context or None."""

    async def load(
        self,
        conversation_id: str,
        request: InteractionRequest | ChatRequest | None = None,
        **kwargs: Any,
    ) -> ConversationContext | None:
        return getattr(request, "context", None) if request else None

    async def save(self, context: ConversationContext, **kwargs: Any) -> None:
        pass


class NoopIntentEngine(IIntentEngine):
    """Null Object intent engine returning None."""

    async def detect_intent(
        self,
        request: InteractionRequest | ChatRequest,
        context: ConversationContext | None = None,
        **kwargs: Any,
    ) -> IntentResult | None:
        return None


class NoopPlanner(IPlanner):
    """Null Object planner returning None."""

    async def create_plan(
        self,
        request: InteractionRequest | ChatRequest,
        intent: Any = None,
        context: ConversationContext | None = None,
        **kwargs: Any,
    ) -> Plan | None:
        return None


class DefaultExecutionEngine(IExecutionEngine):
    """Default execution engine delegating to LLM client or generating fallback response."""

    def __init__(self, llm_client: Any = None, prompt_provider: Any = None) -> None:
        self._llm_client = llm_client
        self._prompt_provider = prompt_provider

    async def execute(
        self,
        request: InteractionRequest | ChatRequest,
        intent: Any = None,
        plan: Any = None,
        context: ConversationContext | None = None,
        **kwargs: Any,
    ) -> PipelineResult:
        if self._llm_client is not None:
            user_input = getattr(request, "user_input", None) or getattr(request, "message", "")
            resolved_prompt = ""
            if self._prompt_provider is not None and hasattr(self._prompt_provider, "resolve_prompt"):
                resolved_prompt = self._prompt_provider.resolve_prompt(request, context)

            chat_req_kwargs: dict[str, Any] = {
                "conversation_id": getattr(request, "conversation_id", None),
                "message": user_input,
                "context": context,
                "metadata": {**getattr(request, "metadata", {}), "resolved_prompt": resolved_prompt},
            }
            from app.schemas.chat import ChatRequest
            chat_req = ChatRequest(**chat_req_kwargs)
            ai_resp = await self._llm_client.generate(chat_req)

            return PipelineResult(
                status=PipelineResultStatus.SUCCEEDED,
                execution_result=ExecutionResult(success=True, output=ai_resp.content, metadata=ai_resp.metadata),
                content=ai_resp.content,
                metadata={
                    "provider": ai_resp.provider,
                    "model": ai_resp.model,
                    "finish_reason": ai_resp.finish_reason or "stop",
                    **ai_resp.metadata,
                },
            )

        user_input = getattr(request, "user_input", None) or getattr(request, "message", "")
        return PipelineResult(
            status=PipelineResultStatus.SUCCEEDED,
            execution_result=ExecutionResult(success=True, output=f"Received: {user_input}"),
            content=f"Received: {user_input}",
        )


class DefaultResponseFormatter(IResponseFormatter):
    """Default response formatter implementing standard InteractionResponse formatting."""

    def format_interaction_response(
        self,
        pipeline_result: PipelineResult | ExecutionResult | AIResponse,
        request: InteractionRequest,
        context: ConversationContext | None = None,
        execution_time_ms: float = 0.0,
    ) -> InteractionResponse:
        content = ""
        success = True
        metadata: dict[str, Any] = {}
        finish_reason = "stop"

        if isinstance(pipeline_result, PipelineResult):
            content = pipeline_result.content
            success = pipeline_result.status == PipelineResultStatus.SUCCEEDED
            metadata = dict(pipeline_result.metadata)
            finish_reason = metadata.get("finish_reason") or ("stop" if success else "error")
        elif isinstance(pipeline_result, ExecutionResult):
            content = pipeline_result.output
            success = pipeline_result.success
            metadata = dict(pipeline_result.metadata)
            finish_reason = "stop" if success else "error"
        elif isinstance(pipeline_result, AIResponse):
            content = pipeline_result.content
            finish_reason = pipeline_result.finish_reason or "stop"
            metadata = dict(pipeline_result.metadata)

        return InteractionResponse(
            response_id=uuid4(),
            request_id=request.request_id,
            session_id=request.session_id,
            conversation_id=request.conversation_id,
            success=success,
            content=content,
            intent=None,
            context=context,
            finish_reason=finish_reason,
            execution_time_ms=execution_time_ms,
            metadata=metadata,
        )

    def format_ai_response(
        self,
        content: str,
        provider: str | None = None,
        model: str | None = None,
        finish_reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AIResponse:
        return AIResponse(
            content=content,
            provider=provider,
            model=model,
            finish_reason=finish_reason,
            metadata=metadata or {},
        )

    def format_error_response(
        self,
        error_message: str,
        finish_reason: str = "error",
        metadata: dict[str, Any] | None = None,
    ) -> AIResponse:
        return AIResponse(
            content=error_message,
            provider=None,
            model=None,
            finish_reason=finish_reason,
            metadata=metadata or {},
        )
