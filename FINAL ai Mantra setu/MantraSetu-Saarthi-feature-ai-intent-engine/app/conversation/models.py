"""Domain models and schemas for the Conversation subsystem in MantraSetu AgentOS.

This module defines immutable Pydantic v2 domain models, message structures, turn representations,
context settings, and session models for framework-independent conversation management.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Mapping
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

Metadata = Mapping[str, object]


def _utc_now() -> datetime:
    """Return the current timestamp in UTC.

    Returns:
        datetime: Current timezone-aware datetime instance in UTC.
    """
    return datetime.now(timezone.utc)


class BaseConversationModel(BaseModel):
    """Base Pydantic v2 model for immutable Conversation domain entities."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )


class ConversationRole(str, Enum):
    """Enumeration of message roles in a conversation context."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ConversationSessionStatus(str, Enum):
    """Enumeration of conversation session operational statuses."""

    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"


# Alias for backward compatibility
ConversationStatus = ConversationSessionStatus


class ConversationContext(BaseConversationModel):
    """Domain model capturing configuration parameters and active contexts for a session.

    Attributes:
        session_id: Optional associated conversation session UUID.
        metadata: Immutable key-value metadata mapping.
        active_intent: Optional active user intent string.
        active_task: Optional active task identifier string.
        rag_context: Immutable RAG retrieval context mapping.
        navigation_context: Immutable navigation state context mapping.
    """

    session_id: UUID | None = Field(
        default=None,
        description="Optional associated conversation session UUID.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable key-value metadata mapping.",
    )
    active_intent: str | None = Field(
        default=None,
        description="Optional active user intent string.",
    )
    active_task: str | None = Field(
        default=None,
        description="Optional active task identifier string.",
    )
    rag_context: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable RAG retrieval context mapping.",
    )
    navigation_context: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable navigation state context mapping.",
    )


class ConversationSession(BaseConversationModel):
    """Domain model representing a conversation session state and metadata.

    Attributes:
        session_id: Unique conversation session identifier UUID.
        conversation_id: Optional associated conversation UUID.
        user_id: Optional associated user UUID.
        context: ConversationContext configuration for the session.
        status: ConversationSessionStatus enum indicating session state.
        created_at: UTC creation timestamp.
        updated_at: UTC last update timestamp.
    """

    session_id: UUID = Field(
        default_factory=uuid4,
        description="Unique conversation session identifier UUID.",
    )
    conversation_id: UUID | None = Field(
        default=None,
        description="Optional associated conversation UUID.",
    )
    user_id: UUID | None = Field(
        default=None,
        description="Optional associated user UUID.",
    )
    context: ConversationContext = Field(
        default_factory=ConversationContext,
        description="ConversationContext configuration for the session.",
    )
    status: ConversationSessionStatus = Field(
        default=ConversationSessionStatus.ACTIVE,
        description="ConversationSessionStatus enum indicating session state.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC creation timestamp.",
    )
    updated_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC last update timestamp.",
    )


class ConversationMessage(BaseConversationModel):
    """Domain model representing a single conversation message.

    Attributes:
        message_id: Unique message identifier UUID.
        session_id: Target session identifier UUID.
        role: Role of the message sender (system, user, assistant, tool).
        content: Text content of the message.
        metadata: Immutable key-value metadata mapping.
        created_at: UTC timestamp when message was created.
    """

    message_id: UUID = Field(
        default_factory=uuid4,
        description="Unique message identifier UUID.",
    )
    session_id: UUID = Field(
        ...,
        description="Target session identifier UUID.",
    )
    role: ConversationRole = Field(
        ...,
        description="Role of the message sender.",
    )
    content: str = Field(
        default="",
        description="Text content of the message.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable key-value metadata mapping.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC message creation timestamp.",
    )


class ConversationTurn(BaseConversationModel):
    """Domain model representing a single interaction turn (user prompt and assistant response).

    Attributes:
        turn_id: Unique turn identifier UUID.
        session_id: Target session identifier UUID.
        user_message: User message that initiated the turn.
        assistant_message: Optional assistant response message.
        created_at: UTC creation timestamp.
    """

    turn_id: UUID = Field(
        default_factory=uuid4,
        description="Unique turn identifier UUID.",
    )
    session_id: UUID = Field(
        ...,
        description="Target session identifier UUID.",
    )
    user_message: ConversationMessage = Field(
        ...,
        description="User message initiating the turn.",
    )
    assistant_message: ConversationMessage | None = Field(
        default=None,
        description="Optional assistant response message.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC turn creation timestamp.",
    )


class ConversationBatch(BaseConversationModel):
    """Domain model representing a batch of conversation messages for bulk processing.

    Attributes:
        batch_id: Unique batch identifier UUID.
        session_id: Target conversation session identifier UUID.
        messages: Immutable tuple of ConversationMessage instances to process.
        created_at: UTC creation timestamp.
    """

    batch_id: UUID = Field(
        default_factory=uuid4,
        description="Unique batch identifier UUID.",
    )
    session_id: UUID = Field(
        ...,
        description="Target conversation session identifier UUID.",
    )
    messages: tuple[ConversationMessage, ...] = Field(
        default_factory=tuple,
        description="Tuple of ConversationMessage instances.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC batch creation timestamp.",
    )
