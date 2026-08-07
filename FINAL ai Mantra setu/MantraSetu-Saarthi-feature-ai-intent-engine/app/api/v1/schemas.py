"""Pydantic v2 request/response schemas for the Chat and Health API endpoints.

Separated from domain models to keep API contracts independent of internal orchestrator models.
"""

from __future__ import annotations

from typing import Mapping
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class _ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatRequest(_ApiModel):
    """Incoming chat request from the frontend.

    Attributes:
        user_input: Raw user message string.
        session_id: Optional user session identifier.
        conversation_id: Optional conversation thread identifier.
        metadata: Optional key-value context metadata.
    """

    user_input: str = Field(..., min_length=1, description="Raw user message string.")
    session_id: UUID | None = Field(default=None, description="Optional user session UUID.")
    conversation_id: UUID | None = Field(default=None, description="Optional conversation thread UUID.")
    metadata: Mapping[str, object] = Field(default_factory=dict, description="Optional context metadata.")


class ChatResponse(_ApiModel):
    """Outgoing chat response to the frontend.

    Attributes:
        request_id: Echo of the originating request UUID.
        success: Whether orchestration succeeded.
        response: Generated response text.
        metadata: Orchestration result metadata.
    """

    request_id: UUID = Field(..., description="Originating request UUID.")
    success: bool = Field(..., description="Whether orchestration succeeded.")
    response: str = Field(..., description="Generated response text.")
    metadata: Mapping[str, object] = Field(default_factory=dict, description="Orchestration result metadata.")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class ComponentHealthSchema(_ApiModel):
    """Health status for a single subsystem component."""

    component_name: str
    status: str
    message: str


class HealthResponse(_ApiModel):
    """Overall application and AI subsystem health response.

    Attributes:
        status: Aggregated health status string.
        healthy: True if all subsystems are operational.
        components: Per-subsystem health details keyed by component name.
    """

    status: str = Field(..., description="Aggregated health status.")
    healthy: bool = Field(..., description="True if all subsystems are operational.")
    components: Mapping[str, ComponentHealthSchema] = Field(
        default_factory=dict,
        description="Per-subsystem component health details.",
    )
