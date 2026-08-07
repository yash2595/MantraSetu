"""Domain models for the Browser Session Manager."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    """Lifecycle status of a browser session."""
    ACTIVE = "ACTIVE"
    IDLE = "IDLE"
    CLOSED = "CLOSED"


class BrowserSession(BaseModel):
    """Immutable model representing an individual browser session.
    
    This is a pure domain model containing only session metadata.
    It deliberately excludes infrastructure objects (Context, Page).
    """
    
    session_id: str
    status: SessionStatus
    created_at: datetime
    last_used_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
