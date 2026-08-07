"""Core conversation schemas shared across the backend."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator

from app.schemas.base import SchemaModel


class EntityKind(StrEnum):
    """Canonical entity categories used across parsing and routing."""

    DATE = "date"
    TIME = "time"
    LOCATION = "location"
    PERSON = "person"
    SERVICE = "service"
    TEMPLE = "temple"
    TEXT = "text"
    NUMBER = "number"
    CUSTOM = "custom"


class NavigationStatus(StrEnum):
    """High-level state of the conversation navigation flow."""

    IDLE = "idle"
    COLLECTING = "collecting"
    ROUTING = "routing"
    READY = "ready"
    BLOCKED = "blocked"
    COMPLETED = "completed"


class Entity(SchemaModel):
    """Extracted structured value from user input or retrieved context.

    Entity objects are reused by the LLM layer, planner, tool calling, memory,
    and RAG components to keep extracted data in one uniform structure.
    """

    name: str = Field(min_length=1, description="Canonical entity name.")
    kind: EntityKind = Field(description="Entity category.")
    value: str | int | float | bool = Field(description="Raw extracted entity value.")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence.")
    source: str | None = Field(default=None, description="Source of the entity, if known.")
    start_index: int | None = Field(default=None, ge=0, description="Optional character start index.")
    end_index: int | None = Field(default=None, ge=0, description="Optional character end index.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional entity metadata.")

    @field_validator("end_index")
    @classmethod
    def validate_end_index(cls, value: int | None, info: Any) -> int | None:
        """Ensure end_index is not lower than start_index when both are present."""
        start_index = info.data.get("start_index")
        if value is not None and start_index is not None and value < start_index:
            raise ValueError("end_index must be greater than or equal to start_index")
        return value


class Intent(SchemaModel):
    """Normalized user intent used for routing and orchestration.

    Intent is intentionally lightweight so it can be produced by an LLM, a rule
    engine, or future classifiers without changing downstream consumers.
    """

    name: str = Field(min_length=1, description="Canonical intent name.")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Classification confidence.")
    description: str | None = Field(default=None, description="Human-readable intent summary.")
    entities: list[Entity] = Field(default_factory=list, description="Entities attached to the intent.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional intent metadata.")


class NavigationState(SchemaModel):
    """Track the current routing and conversation navigation status."""

    status: NavigationStatus = Field(default=NavigationStatus.IDLE, description="Navigation state.")
    current_route: str | None = Field(default=None, description="Current route or flow name.")
    active_step: str | None = Field(default=None, description="Current step within the route.")
    next_step: str | None = Field(default=None, description="Next expected step.")
    message: str | None = Field(default=None, description="Optional human-readable status message.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional navigation metadata.")


class ConversationContext(SchemaModel):
    """Shared runtime context for a single conversation or session.

    This schema gives every module a single typed object for state handoff,
    which keeps future agent, planner, memory, and RAG integration consistent.
    """

    conversation_id: str = Field(min_length=1, description="Unique conversation identifier.")
    user_id: str | None = Field(default=None, description="Optional user identifier.")
    session_id: str | None = Field(default=None, description="Optional session identifier.")
    channel: str | None = Field(default=None, description="Channel or surface where the conversation runs.")
    locale: str = Field(default="en", min_length=2, description="Conversation locale.")
    timezone: str | None = Field(default=None, description="User timezone, if available.")
    intent: Intent | None = Field(default=None, description="Resolved intent for the current turn.")
    navigation_state: NavigationState = Field(default_factory=NavigationState, description="Navigation state.")
    entities: list[Entity] = Field(default_factory=list, description="Conversation-level entities.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Free-form conversation metadata.")
