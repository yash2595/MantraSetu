"""Domain models and schemas for the Orchestrator subsystem in MantraSetu AgentOS.

This module defines immutable Pydantic v2 domain models for user requests, intent detection,
execution routing, orchestrator context, and orchestrator response outputs.
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


class BaseOrchestratorModel(BaseModel):
    """Base Pydantic v2 model for immutable Orchestrator domain entities."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )


class IntentType(str, Enum):
    """Enumeration of detected user intent classification types."""

    CHAT = "chat"
    INFORMATION_QUERY = "information_query"
    NAVIGATION_TASK = "navigation_task"
    BOOKING_TASK = "booking_task"
    SPIRITUAL_SERVICE = "spiritual_service"
    UNKNOWN = "unknown"


class UserRequest(BaseOrchestratorModel):
    """Domain model representing an incoming user interaction request.

    Attributes:
        request_id: Unique request identifier UUID.
        user_input: Raw user text input string.
        session_id: Optional associated user session identifier UUID.
        conversation_id: Optional associated conversation identifier UUID.
        metadata: Immutable key-value metadata mapping.
        created_at: UTC creation timestamp.
    """

    request_id: UUID = Field(
        default_factory=uuid4,
        description="Unique request identifier UUID.",
    )
    user_input: str = Field(
        ...,
        description="Raw user text input string.",
    )
    session_id: UUID | None = Field(
        default=None,
        description="Optional associated user session identifier UUID.",
    )
    conversation_id: UUID | None = Field(
        default=None,
        description="Optional associated conversation identifier UUID.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable key-value metadata mapping.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC creation timestamp.",
    )


class DetectedIntent(BaseOrchestratorModel):
    """Domain model representing a classified user intent with confidence score.

    Attributes:
        intent_id: Unique detection result identifier UUID.
        intent_type: IntentType enum classification value.
        confidence: Floating-point confidence score between 0.0 and 1.0.
        entities: Immutable extracted entity key-value mapping.
    """

    intent_id: UUID = Field(
        default_factory=uuid4,
        description="Unique detection result identifier UUID.",
    )
    intent_type: IntentType = Field(
        default=IntentType.UNKNOWN,
        description="IntentType enum classification value.",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Floating-point confidence score between 0.0 and 1.0.",
    )
    entities: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable extracted entity key-value mapping.",
    )


class ExecutionRoute(BaseOrchestratorModel):
    """Domain model representing a resolved service execution routing plan.

    Attributes:
        route_id: Unique route identifier UUID.
        intent: IntentType enum value that triggered this route.
        services: Immutable tuple of service name strings to invoke.
    """

    route_id: UUID = Field(
        default_factory=uuid4,
        description="Unique route identifier UUID.",
    )
    intent: IntentType = Field(
        ...,
        description="IntentType enum value that triggered this route.",
    )
    services: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Immutable tuple of service name strings to invoke.",
    )


class OrchestratorContext(BaseOrchestratorModel):
    """Domain model consolidating complete orchestrator execution context for a request.

    Attributes:
        request_id: Associated UserRequest identifier UUID.
        session_id: Optional associated user session identifier UUID.
        detected_intent: Optional DetectedIntent model from intent classification.
        route: Optional ExecutionRoute model resolved for this request.
        metadata: Immutable key-value metadata mapping.
    """

    request_id: UUID = Field(
        ...,
        description="Associated UserRequest identifier UUID.",
    )
    session_id: UUID | None = Field(
        default=None,
        description="Optional associated user session identifier UUID.",
    )
    detected_intent: DetectedIntent | None = Field(
        default=None,
        description="Optional DetectedIntent model from intent classification.",
    )
    route: ExecutionRoute | None = Field(
        default=None,
        description="Optional ExecutionRoute model resolved for this request.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable key-value metadata mapping.",
    )


class OrchestratorResponse(BaseOrchestratorModel):
    """Domain model representing the final orchestrated response to a user request.

    Attributes:
        request_id: Associated UserRequest identifier UUID.
        success: Boolean flag indicating if orchestration succeeded.
        response: Final response text string to return to the user.
        metadata: Immutable key-value metadata mapping.
    """

    request_id: UUID = Field(
        ...,
        description="Associated UserRequest identifier UUID.",
    )
    success: bool = Field(
        ...,
        description="Boolean flag indicating if orchestration succeeded.",
    )
    response: str = Field(
        default="",
        description="Final response text string to return to the user.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable key-value metadata mapping.",
    )
