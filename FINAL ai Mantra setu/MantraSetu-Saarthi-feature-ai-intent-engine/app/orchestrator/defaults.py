"""
Default dependency composition for the MantraSetu AI Backend.

This module wires together all default implementations required by the
ChatOrchestrator. Every dependency can later be replaced by Memory,
RAG, Planner, Navigation, Tool Calling, etc.
"""

from __future__ import annotations

from typing import Any

from app.llm.providers.gemini import GeminiProvider
from app.orchestrator.chat_orchestrator import ChatOrchestrator
from app.orchestrator.context import OrchestratorDependencies
from app.orchestrator.base import (
    ConversationContextLoader,
    RoutingPolicy,
    StructuredOutputParser,
)
from app.prompts.prompt_manager import PromptManager
from app.schemas.chat import AIResponse, ChatResponse
from app.schemas.context import (
    ConversationContext,
    Intent,
    NavigationState,
)


class NoopConversationContextLoader(ConversationContextLoader):
    """Temporary conversation loader."""

    async def load(
        self,
        conversation_id: str,
        **kwargs: Any,
    ) -> ConversationContext | None:
        return None

    async def save(
        self,
        context: ConversationContext,
        **kwargs: Any,
    ) -> None:
        return None


class PassThroughStructuredOutputParser(StructuredOutputParser):
    """Simple parser until structured outputs are introduced."""

    def parse_ai_response(
        self,
        raw_output: str,
        **kwargs: Any,
    ) -> AIResponse:
        return AIResponse(
            content=raw_output,
        )

    def parse_chat_response(
        self,
        raw_output: str,
        **kwargs: Any,
    ) -> ChatResponse:
        return ChatResponse(
            assistant_message=raw_output,
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


class DefaultRoutingPolicy(RoutingPolicy):
    """Everything disabled until Planner/Navigation is implemented."""

    def requires_rag(
        self,
        intent: Intent | None,
        ai_response: AIResponse | None,
        **kwargs: Any,
    ) -> bool:
        return False

    def requires_tool_call(
        self,
        intent: Intent | None,
        ai_response: AIResponse | None,
        **kwargs: Any,
    ) -> bool:
        return False

    def requires_navigation(
        self,
        intent: Intent |None,
        navigation_state: NavigationState | None,
        **kwargs: Any,
    ) -> bool:
        return False

    def requires_planner(
        self,
        intent: Intent | None,
        ai_response: AIResponse | None,
        **kwargs: Any,
    ) -> bool:
        return False


from app.orchestrator.ai_orchestrator import AIOrchestrator
from app.orchestrator.builder import AIOrchestratorBuilder


def build_ai_orchestrator() -> AIOrchestrator:
    """Build the primary AIOrchestrator instance."""
    return AIOrchestrator()


def build_chat_orchestrator() -> ChatOrchestrator:
    """Build legacy ChatOrchestrator compatibility wrapper over AIOrchestrator."""
    ai_orch = build_ai_orchestrator()
    # Provide dummy dependencies since the new AIOrchestrator handles its own
    parser = PassThroughStructuredOutputParser()
    dependencies = OrchestratorDependencies(
        context_loader=NoopConversationContextLoader(),
        prompt_provider=PromptManager(),
        llm_client=GeminiProvider(),
        output_parser=parser,
        routing_policy=DefaultRoutingPolicy(),
        response_formatter=parser,
    )
    return ChatOrchestrator(
        dependencies=dependencies,
        ai_orchestrator=ai_orch,
    )