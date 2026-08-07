"""Memory schema for persisted conversation and agent state."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from app.schemas.base import SchemaModel
from app.schemas.context import ConversationContext, Entity, Intent, NavigationState


class MemoryScope(StrEnum):
    """Where a memory record applies."""

    SESSION = "session"
    CONVERSATION = "conversation"
    USER = "user"
    GLOBAL = "global"


class MemoryRecordType(StrEnum):
    """Canonical memory record type."""

    FACT = "fact"
    PREFERENCE = "preference"
    STATE = "state"
    SUMMARY = "summary"
    EVENT = "event"


class MemoryRecord(SchemaModel):
    """Persistent memory entry used by memory and retrieval systems.

    This schema is intentionally generic so it can store facts, summaries,
    preferences, state snapshots, and future retrieval artifacts without changing
    the storage contract.
    """

    record_id: UUID = Field(default_factory=uuid4, description="Unique memory record identifier.")
    scope: MemoryScope = Field(default=MemoryScope.SESSION, description="Memory scope.")
    record_type: MemoryRecordType = Field(default=MemoryRecordType.FACT, description="Memory type.")
    key: str = Field(min_length=1, description="Stable lookup key for the record.")
    value: str | dict[str, Any] | list[Any] | int | float | bool | None = Field(
        default=None,
        description="Stored memory payload.",
    )
    conversation_context: ConversationContext | None = Field(default=None, description="Optional linked conversation context.")
    intent: Intent | None = Field(default=None, description="Optional related intent.")
    navigation_state: NavigationState | None = Field(default=None, description="Optional related navigation state.")
    entities: list[Entity] = Field(default_factory=list, description="Entities associated with the record.")
    source: str | None = Field(default=None, description="Source of the memory record.")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the record was created.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the record was last updated.",
    )
    expires_at: datetime | None = Field(default=None, description="Optional expiration timestamp.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional memory metadata.")
