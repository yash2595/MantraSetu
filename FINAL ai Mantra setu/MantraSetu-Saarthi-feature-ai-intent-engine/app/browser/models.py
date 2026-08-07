"""Domain models and schemas for the Browser Automation subsystem in MantraSetu AgentOS.

This module defines immutable Pydantic v2 domain models for browser sessions, pages,
action execution results, and operational statuses without coupling to Playwright or browser SDKs.
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


class BaseBrowserModel(BaseModel):
    """Base Pydantic v2 model for immutable Browser domain entities."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )


class BrowserStatus(str, Enum):
    """Enumeration of browser session operational statuses."""

    ACTIVE = "active"
    IDLE = "idle"
    CLOSED = "closed"
    ERROR = "error"


class BrowserActionResultStatus(str, Enum):
    """Enumeration of browser action execution outcomes."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class BrowserSession(BaseBrowserModel):
    """Domain model representing an active browser automation session.

    Attributes:
        session_id: Unique browser session identifier UUID.
        status: BrowserStatus enum value.
        metadata: Immutable key-value metadata mapping.
        created_at: UTC creation timestamp.
        updated_at: UTC last update timestamp.
    """

    session_id: UUID = Field(
        default_factory=uuid4,
        description="Unique browser session identifier UUID.",
    )
    status: BrowserStatus = Field(
        default=BrowserStatus.ACTIVE,
        description="BrowserStatus enum value.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable key-value metadata mapping.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC creation timestamp.",
    )
    updated_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC last update timestamp.",
    )


class BrowserPage(BaseBrowserModel):
    """Domain model representing a loaded web page state in the browser.

    Attributes:
        page_id: Unique page identifier UUID.
        session_id: Associated browser session identifier UUID.
        url: Page URL string.
        title: Page document title string.
        content: HTML or text page content snapshot string.
        created_at: UTC page capture timestamp.
    """

    page_id: UUID = Field(
        default_factory=uuid4,
        description="Unique page identifier UUID.",
    )
    session_id: UUID = Field(
        ...,
        description="Associated browser session identifier UUID.",
    )
    url: str = Field(
        ...,
        description="Page URL string.",
    )
    title: str = Field(
        default="",
        description="Page document title string.",
    )
    content: str = Field(
        default="",
        description="HTML or text page content snapshot string.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC page capture timestamp.",
    )


class BrowserActionResult(BaseBrowserModel):
    """Domain model capturing the result of a browser action execution.

    Attributes:
        action_id: Unique action identifier UUID.
        status: BrowserActionResultStatus enum value.
        error_message: Optional error message string if action failed.
        screenshot_path: Optional file path string to captured action screenshot.
        execution_time_ms: Total execution duration in milliseconds.
        created_at: UTC action result creation timestamp.
    """

    action_id: UUID = Field(
        ...,
        description="Unique action identifier UUID.",
    )
    status: BrowserActionResultStatus = Field(
        default=BrowserActionResultStatus.SUCCESS,
        description="BrowserActionResultStatus enum value.",
    )
    error_message: str | None = Field(
        default=None,
        description="Optional error message string if action failed.",
    )
    screenshot_path: str | None = Field(
        default=None,
        description="Optional file path string to captured action screenshot.",
    )
    execution_time_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Total execution duration in milliseconds.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC action result creation timestamp.",
    )
