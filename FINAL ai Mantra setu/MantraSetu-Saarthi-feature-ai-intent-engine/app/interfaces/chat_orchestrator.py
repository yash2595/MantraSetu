"""Frozen abstract interface contracts for MantraSetu AI Orchestration Subsystem.

This module defines standard Protocols and Abstract Base Classes (ABCs) for all
subsystem collaborators: ISessionManager, IContextManager, IIntentEngine, IPlanner,
IExecutionEngine, IResponseFormatter, IPromptProvider, IPipelineExecutor, IPipelineStage,
and IEventPublisher.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from app.schemas.api.interaction import InteractionRequest, InteractionResponse
from app.schemas.chat import AIResponse, ChatRequest
from app.schemas.context import ConversationContext, Intent
from app.schemas.domain.interaction import (
    ExecutionResult,
    IntentResult,
    PipelineResult,
    Plan,
)
from app.schemas.planner import PlannerResponse

if TYPE_CHECKING:
    from app.orchestrator.events import OrchestrationEvent
    from app.orchestrator.execution_context import ExecutionContext


@runtime_checkable
class ISessionManager(Protocol):
    """Abstract protocol for Session Management."""

    async def load_session(
        self,
        session_id: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Load session state for session_id."""
        ...

    async def save_session(
        self,
        session_id: str,
        session_data: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Persist updated session state."""
        ...


@runtime_checkable
class IContextManager(Protocol):
    """Abstract protocol for Context Management."""

    async def load(
        self,
        conversation_id: str,
        request: InteractionRequest | ChatRequest | None = None,
        **kwargs: Any,
    ) -> ConversationContext | None:
        """Load conversation context for conversation_id."""
        ...

    async def save(
        self,
        context: ConversationContext,
        **kwargs: Any,
    ) -> None:
        """Persist updated conversation context."""
        ...


@runtime_checkable
class IIntentEngine(Protocol):
    """Abstract protocol for Intent Detection Engine."""

    async def detect_intent(
        self,
        request: InteractionRequest | ChatRequest,
        context: ConversationContext | None = None,
        **kwargs: Any,
    ) -> IntentResult | Intent | None:
        """Classify user intent from request and context."""
        ...


@runtime_checkable
class IPlanner(Protocol):
    """Abstract protocol for Execution Planner."""

    async def create_plan(
        self,
        request: InteractionRequest | ChatRequest,
        intent: IntentResult | Intent | None = None,
        context: ConversationContext | None = None,
        **kwargs: Any,
    ) -> Plan | PlannerResponse | None:
        """Generate an execution plan based on intent and context."""
        ...


@runtime_checkable
class IExecutionEngine(Protocol):
    """Abstract protocol for Execution Engine."""

    async def execute(
        self,
        request: InteractionRequest | ChatRequest,
        intent: IntentResult | Intent | None = None,
        plan: Plan | PlannerResponse | None = None,
        context: ConversationContext | None = None,
        **kwargs: Any,
    ) -> PipelineResult | ExecutionResult | AIResponse:
        """Execute downstream operations and generate result."""
        ...


@runtime_checkable
class ILLMManager(Protocol):
    """Abstract protocol for LLM Client / Manager."""

    async def generate(
        self,
        request: ChatRequest,
        **kwargs: Any,
    ) -> AIResponse:
        """Generate AI response for chat request."""
        ...


@runtime_checkable
class IResponseFormatter(Protocol):
    """Abstract protocol for Response Formatter."""

    def format_interaction_response(
        self,
        pipeline_result: PipelineResult | ExecutionResult | AIResponse,
        request: InteractionRequest,
        context: ConversationContext | None = None,
        execution_time_ms: float = 0.0,
    ) -> InteractionResponse:
        """Format pipeline result into standard InteractionResponse."""
        ...

    def format_ai_response(
        self,
        content: str,
        provider: str | None = None,
        model: str | None = None,
        finish_reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AIResponse:
        """Format raw output into AIResponse."""
        ...

    def format_error_response(
        self,
        error_message: str,
        finish_reason: str = "error",
        metadata: dict[str, Any] | None = None,
    ) -> AIResponse:
        """Format an error into AIResponse."""
        ...


@runtime_checkable
class IPromptProvider(Protocol):
    """Abstract protocol for Prompt Provider."""

    def resolve_prompt(
        self,
        request: InteractionRequest | ChatRequest,
        context: ConversationContext | None = None,
    ) -> str:
        """Resolve system prompt without exposing business logic."""
        ...


@runtime_checkable
class IPipelineStage(Protocol):
    """Abstract protocol for an individual Pipeline Stage."""

    @property
    def stage_name(self) -> str:
        """Unique human-readable stage name."""
        ...

    async def execute(self, context: ExecutionContext) -> ExecutionContext:
        """Execute stage logic, update owned context field, and return updated context."""
        ...


@runtime_checkable
class IPipelineExecutor(Protocol):
    """Abstract protocol for Pipeline Executor managing stage execution flow."""

    async def execute_pipeline(
        self,
        request: InteractionRequest,
    ) -> InteractionResponse:
        """Execute all registered pipeline stages sequentially."""
        ...


@runtime_checkable
class IEventPublisher(Protocol):
    """Abstract protocol for structured lifecycle domain event publishing."""

    def publish(self, event: OrchestrationEvent) -> None:
        """Publish a lifecycle domain event."""
        ...
