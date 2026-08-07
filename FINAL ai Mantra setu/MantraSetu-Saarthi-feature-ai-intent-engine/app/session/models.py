"""Domain models for application session management in MantraSetu AgentOS.

This module defines immutable Pydantic v2 domain models for tracking user sessions,
session contexts, activity events, and session operational statuses.
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


class BaseSessionModel(BaseModel):
    """Base Pydantic v2 model for immutable session domain entities."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )


class SessionStatus(str, Enum):
    """Enumeration of user session operational statuses."""

    ACTIVE = "active"
    EXPIRED = "expired"
    CLOSED = "closed"


class UserSession(BaseSessionModel):
    """Domain model representing an active application user session.

    Attributes:
        session_id: Unique session identifier UUID.
        user_id: Optional associated user identifier UUID.
        status: Current SessionStatus enum value.
        metadata: Immutable key-value metadata mapping.
        created_at: UTC session creation timestamp.
        updated_at: UTC session last update timestamp.
        expires_at: Optional UTC session expiration timestamp.
    """

    session_id: UUID = Field(
        default_factory=uuid4,
        description="Unique session identifier UUID.",
    )
    user_id: UUID | None = Field(
        default=None,
        description="Optional associated user identifier UUID.",
    )
    status: SessionStatus = Field(
        default=SessionStatus.ACTIVE,
        description="Current SessionStatus enum value.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable key-value metadata mapping.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC session creation timestamp.",
    )
    updated_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC session last update timestamp.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Optional UTC session expiration timestamp.",
    )


class SessionContext(BaseSessionModel):
    """Domain model capturing active state and route context for a session.

    Attributes:
        session_id: Associated unique session identifier UUID.
        conversation_id: Optional associated conversation UUID.
        active_route: Optional current UI navigation route string.
        state: Immutable application state mapping.
        metadata: Immutable key-value metadata mapping.
    """

    session_id: UUID = Field(
        default_factory=uuid4,
        description="Associated unique session identifier UUID.",
    )
    conversation_id: UUID | None = Field(
        default=None,
        description="Optional associated conversation UUID.",
    )
    active_route: str | None = Field(
        default=None,
        description="Optional current UI navigation route string.",
    )
    state: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable application state mapping.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable key-value metadata mapping.",
    )


class SessionActivity(BaseSessionModel):
    """Domain model representing a discrete user or system action during a session.

    Attributes:
        activity_id: Unique activity identifier UUID.
        session_id: Associated session identifier UUID.
        action: Action name or event identifier string.
        metadata: Immutable activity metadata mapping.
        created_at: UTC activity creation timestamp.
    """

    activity_id: UUID = Field(
        default_factory=uuid4,
        description="Unique activity identifier UUID.",
    )
    session_id: UUID = Field(
        ...,
        description="Associated session identifier UUID.",
    )
    action: str = Field(
        ...,
        description="Action name or event identifier string.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable activity metadata mapping.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC activity creation timestamp.",
    )
