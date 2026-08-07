"""Pydantic v2 request/response schemas for the Conversation API endpoint.

These schemas form the public API contract for POST /api/v1/conversation/chat.
They are intentionally independent of internal orchestrator domain models so
the API surface can evolve without coupling to execution internals.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import Field, field_validator

from app.schemas.base import SchemaModel


class ConversationRequest(SchemaModel):
    """Incoming request payload for the Conversation API endpoint.

    Attributes:
        session_id: Client-assigned session identifier for tracking conversation turns.
        message:    Raw user message text. Whitespace is trimmed automatically.
        user_id:    Optional caller user identifier for personalisation or audit.
        metadata:   Optional free-form key-value context forwarded to the orchestrator.

    Validation:
        - ``message`` must be non-empty after whitespace trimming.
        - ``message`` must not exceed 4 000 characters.
    """

    session_id: str = Field(
        ...,
        description="Client-assigned session identifier.",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="User message text (1–4000 characters, whitespace trimmed).",
    )
    user_id: Optional[str] = Field(
        default=None,
        description="Optional caller user identifier.",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional free-form key-value metadata.",
    )

    @field_validator("message", mode="before")
    @classmethod
    def _strip_and_require_message(cls, value: Any) -> str:
        """Strip surrounding whitespace and reject blank messages."""
        if not isinstance(value, str):
            raise ValueError("message must be a string.")
        stripped = value.strip()
        if not stripped:
            raise ValueError("message cannot be empty or contain only whitespace.")
        return stripped


class ConversationResponse(SchemaModel):
    """Outgoing response payload for the Conversation API endpoint.

    Attributes:
        success:    ``True`` when the orchestration pipeline completed without error.
        response:   Final user-facing assistant reply text.
        session_id: Echo of the ``session_id`` supplied in the request.
        timestamp:  UTC timestamp of when this response was produced.
        metadata:   Optional orchestration metadata forwarded from the pipeline.
    """

    success: bool = Field(
        ...,
        description="True when orchestration completed without error.",
    )
    response: str = Field(
        ...,
        description="Final user-facing assistant reply text.",
    )
    session_id: str = Field(
        ...,
        description="Echo of the session_id from the originating request.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of response production.",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional orchestration metadata.",
    )
