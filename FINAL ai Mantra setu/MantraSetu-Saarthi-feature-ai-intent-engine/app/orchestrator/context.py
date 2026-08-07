"""Orchestrator runtime context and dependency containers.

This module keeps mutable request state separate from injected dependencies so
replacing a collaborator never requires changing the orchestrator itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from app.orchestrator.base import (
    ConversationContextLoader,
    LLMClient,
    MemoryGateway,
    NavigationGateway,
    PlannerGateway,
    PromptProvider,
    RAGGateway,
    RoutingPolicy,
    StructuredOutputParser,
    ToolGateway,
    ToolRegistry,
)
from app.schemas.chat import AIResponse, ChatRequest, ChatResponse
from app.schemas.context import ConversationContext, Intent, NavigationState
from app.schemas.memory import MemoryRecord
from app.schemas.planner import PlannerResponse
from app.schemas.tools import ToolCall, ToolResult


@dataclass(slots=True)
class OrchestratorDependencies:
    """Injected collaborator bundle for the orchestrator.

    Every field is replaceable. Optional components can be left unset until the
    corresponding module is available.
    """

    context_loader: ConversationContextLoader
    prompt_provider: PromptProvider
    llm_client: LLMClient
    output_parser: StructuredOutputParser
    routing_policy: RoutingPolicy
    session_manager: Any | None = None
    context_manager: Any | None = None
    intent_engine: Any | None = None
    planner: Any | None = None
    execution_engine: Any | None = None
    response_formatter: Any | None = None
    memory_gateway: MemoryGateway | None = None
    rag_gateway: RAGGateway | None = None
    planner_gateway: PlannerGateway | None = None
    navigation_gateway: NavigationGateway | None = None
    tool_registry: ToolRegistry | None = None
    tool_gateway: ToolGateway | None = None


@dataclass(slots=True)
class OrchestratorState:
    """Mutable request-scoped state passed through orchestration stages."""

    request_id: UUID = field(default_factory=uuid4)
    request: ChatRequest | None = None
    conversation_context: ConversationContext | None = None
    resolved_prompt: str | None = None
    ai_response: AIResponse | None = None
    intent: Intent | None = None
    navigation_state: NavigationState | None = None
    planner_response: PlannerResponse | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    memory_records: list[MemoryRecord] = field(default_factory=list)
    final_response: ChatResponse | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class OrchestratorContext:
    """Top-level orchestration bundle for a single chat turn."""

    dependencies: OrchestratorDependencies
    state: OrchestratorState = field(default_factory=OrchestratorState)
