"""Provider-independent domain models and schemas for the AI subsystem in MantraSetu AgentOS.

This module defines framework-independent, immutable Pydantic v2 domain models for AI conversation,
request handling, response generation, and token tracking, avoiding LLM provider SDK coupling and business logic.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Mapping
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def _utc_now() -> datetime:
    """Return the current timestamp in UTC.

    Returns:
        datetime: Current timezone-aware datetime instance in UTC.
    """
    return datetime.now(timezone.utc)


class BaseAIModel(BaseModel):
    """Base Pydantic v2 model for immutable AI domain entities."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )


class MessageRole(str, Enum):
    """Enumeration of message roles in an AI conversation context."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class AIStatus(str, Enum):
    """Enumeration of AI execution outcomes and statuses."""

    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class Message(BaseAIModel):
    """Domain model representing a single conversation message.

    Attributes:
        message_id: Unique message identifier UUID.
        role: MessageRole enum value.
        content: Text message content.
        metadata: Strongly typed metadata key-value mapping.
        created_at: UTC message creation timestamp.
    """

    message_id: UUID = Field(
        default_factory=uuid4,
        description="Unique message identifier UUID.",
    )
    role: MessageRole = Field(
        ...,
        description="MessageRole enum value.",
    )
    content: str = Field(
        default="",
        description="Text message content.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Strongly typed metadata key-value mapping.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC message creation timestamp.",
    )


class Conversation(BaseAIModel):
    """Domain model representing a user conversation session.

    Attributes:
        conversation_id: Unique conversation session identifier UUID.
        user_id: Optional user identifier UUID.
        messages: Immutable tuple of Message objects.
        metadata: Strongly typed metadata key-value mapping.
        created_at: UTC session creation timestamp.
        updated_at: UTC session last update timestamp.
    """

    conversation_id: UUID = Field(
        default_factory=uuid4,
        description="Unique conversation session identifier UUID.",
    )
    user_id: UUID | None = Field(
        default=None,
        description="Optional user identifier UUID.",
    )
    messages: tuple[Message, ...] = Field(
        default_factory=tuple,
        description="Immutable tuple of Message objects.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Strongly typed metadata key-value mapping.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC session creation timestamp.",
    )
    updated_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC session last update timestamp.",
    )


class TokenUsage(BaseAIModel):
    """Domain model tracking AI model token consumption metrics.

    Attributes:
        input_tokens: Number of prompt/input tokens consumed.
        output_tokens: Number of completion/output tokens generated.
        total_tokens: Total token count consumed.
    """

    input_tokens: int = Field(
        default=0,
        ge=0,
        description="Number of prompt/input tokens consumed.",
    )
    output_tokens: int = Field(
        default=0,
        ge=0,
        description="Number of completion/output tokens generated.",
    )
    total_tokens: int = Field(
        default=0,
        ge=0,
        description="Total token count consumed.",
    )


class AIRequest(BaseAIModel):
    """Domain model representing an incoming AI generation request.

    Attributes:
        request_id: Unique request identifier UUID.
        message: Input Message object.
        conversation_id: Optional associated conversation UUID.
        model: Optional model identifier string.
        context: Context mapping supporting RAG, Navigation, and Memory contexts.
        created_at: UTC request creation timestamp.
    """

    request_id: UUID = Field(
        default_factory=uuid4,
        description="Unique request identifier UUID.",
    )
    message: Message = Field(
        ...,
        description="Input Message object.",
    )
    conversation_id: UUID | None = Field(
        default=None,
        description="Optional associated conversation UUID.",
    )
    model: str | None = Field(
        default=None,
        description="Optional model identifier string.",
    )
    context: Mapping[str, object] = Field(
        default_factory=dict,
        description="Context mapping supporting RAG, Navigation, and Memory contexts.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC request creation timestamp.",
    )


class AIResponse(BaseAIModel):
    """Domain model representing an AI generated response.

    Attributes:
        response_id: Unique response identifier UUID.
        request_id: Associated request identifier UUID.
        content: Generated response text content string.
        model: Model identifier string that generated response.
        status: AIStatus enum indicating response outcome.
        usage: TokenUsage object tracking token consumption.
        execution_time_ms: Total execution duration in milliseconds.
        metadata: Strongly typed metadata key-value mapping.
        created_at: UTC response creation timestamp.
    """

    response_id: UUID = Field(
        default_factory=uuid4,
        description="Unique response identifier UUID.",
    )
    request_id: UUID = Field(
        ...,
        description="Associated request identifier UUID.",
    )
    content: str = Field(
        ...,
        description="Generated response text content string.",
    )
    model: str = Field(
        default="",
        description="Model identifier string that generated response.",
    )
    status: AIStatus = Field(
        default=AIStatus.SUCCESS,
        description="AIStatus enum indicating response outcome.",
    )
    usage: TokenUsage = Field(
        default_factory=TokenUsage,
        description="TokenUsage object tracking token consumption.",
    )
    execution_time_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Total execution duration in milliseconds.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Strongly typed metadata key-value mapping.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC response creation timestamp.",
    )
