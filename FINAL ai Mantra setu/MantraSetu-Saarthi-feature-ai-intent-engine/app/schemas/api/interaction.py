"""API models for normalized transport-agnostic interaction payloads."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from app.schemas.base import SchemaModel
from app.schemas.context import ConversationContext, Intent, NavigationState
from app.schemas.domain.interaction import ExecutionResult


class InteractionRequest(SchemaModel):
    """Normalized API request payload for AI interactions."""

    request_id: UUID = Field(default_factory=uuid4, description="Unique request identifier.")
    session_id: str | None = Field(default=None, description="Active session identifier.")
    conversation_id: UUID | None = Field(default=None, description="Active conversation identifier.")
    user_input: str = Field(min_length=1, description="Normalized user text input string.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional request metadata.")


class InteractionResponse(SchemaModel):
    """Normalized API response payload for AI interactions."""

    response_id: UUID = Field(default_factory=uuid4, description="Unique response identifier.")
    request_id: UUID | None = Field(default=None, description="Correlated request identifier.")
    session_id: str | None = Field(default=None, description="Session identifier.")
    conversation_id: UUID | None = Field(default=None, description="Conversation identifier.")
    success: bool = Field(default=True, description="Whether orchestration succeeded.")
    content: str = Field(default="", description="User-facing assistant output text.")
    intent: Intent | None = Field(default=None, description="Detected intent model.")
    execution_result: ExecutionResult | None = Field(default=None, description="Execution result snapshot.")
    navigation_state: NavigationState | None = Field(default=None, description="Updated navigation state.")
    context: ConversationContext | None = Field(default=None, description="Loaded conversation context snapshot.")
    finish_reason: str | None = Field(default=None, description="Reason generation finished.")
    execution_time_ms: float | None = Field(default=None, description="Total execution latency in milliseconds.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Response metadata.")
