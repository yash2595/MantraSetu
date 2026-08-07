"""Chat and AI response schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from app.schemas.base import SchemaModel
from app.schemas.context import ConversationContext, Entity, Intent, NavigationState


class AIResponse(SchemaModel):
    """Provider-agnostic AI output used across the backend.

    This schema intentionally represents the generic result of an AI call rather
    than a chat-specific payload so it can be reused by the LLM and planner
    layers without introducing adapter-specific fields.
    """

    content: str = Field(min_length=1, description="Final generated text content.")
    provider: str | None = Field(default=None, description="LLM provider name, if known.")
    model: str | None = Field(default=None, description="Model identifier used for generation.")
    finish_reason: str | None = Field(default=None, description="Why generation stopped.")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the response object was created.",
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional response metadata.")


class ChatRequest(SchemaModel):
    """Standard request payload for conversational endpoints."""

    conversation_id: UUID | None = Field(default=None, description="Existing conversation identifier.")
    message: str = Field(min_length=1, description="User message text.")
    context: ConversationContext | None = Field(default=None, description="Optional conversation context.")
    stream: bool = Field(default=False, description="Whether the caller wants a streaming response.")
    language: str | None = Field(default=None, description="Optional preferred response language.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional request metadata.")


class ChatResponse(SchemaModel):
    """Standard response payload for conversational endpoints."""

    response_id: UUID = Field(default_factory=uuid4, description="Unique identifier for this response.")
    conversation_id: UUID | None = Field(default=None, description="Conversation identifier for correlation.")
    assistant_message: str = Field(min_length=1, description="Final user-facing assistant message.")
    ai_response: AIResponse | None = Field(default=None, description="Underlying AI response details.")
    intent: Intent | None = Field(default=None, description="Detected intent for the current turn.")
    entities: list[Entity] = Field(default_factory=list, description="Entities extracted for this turn.")
    navigation_state: NavigationState | None = Field(default=None, description="Updated navigation state.")
    context: ConversationContext | None = Field(default=None, description="Optional updated conversation context.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional response metadata.")
