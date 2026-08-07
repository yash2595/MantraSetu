"""Domain models for the Browser Page abstraction.

These Pydantic v2 models define the data contract for browser page management.
They are intentionally minimal and free of any Playwright, DOM, or automation
specifics so the Browser Page can evolve — adding multiple tabs, popup windows,
events, and network monitoring — without changing the public interface.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import Field

from app.schemas.base import SchemaModel


# ---------------------------------------------------------------------------
# Page state enumeration
# ---------------------------------------------------------------------------


class PageState(str, Enum):
    """Lifecycle state of a browser page.

    Values:
        NOT_CREATED: Page has not been created yet or no longer exists.
        READY:       Page is created and ready for interaction.
        CLOSED:      Page has been intentionally closed.
        FAILED:      Page encountered an unrecoverable error.
    """

    NOT_CREATED = "not_created"
    READY = "ready"
    CLOSED = "closed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Browser page result model
# ---------------------------------------------------------------------------


class BrowserPageResult(SchemaModel):
    """Immutable result produced by Browser Page lifecycle methods.

    The service always returns one of these — it never returns ``None``.

    Attributes:
        success:  ``True`` if the requested lifecycle operation succeeded.
        state:    The current state of the browser page after the operation.
        url:      The current URL of the page, if available.
        title:    The current title of the page, if available.
        message:  Human-readable outcome or status message.
        metadata: Optional free-form context forwarded to callers.
    """

    success: bool = Field(
        ...,
        description="True if the lifecycle operation succeeded.",
    )
    state: PageState = Field(
        default=PageState.NOT_CREATED,
        description="Current state of the browser page.",
    )
    url: Optional[str] = Field(
        default=None,
        description="Current URL of the page, if available.",
    )
    title: Optional[str] = Field(
        default=None,
        description="Current title of the page, if available.",
    )
    message: str = Field(
        default="",
        description="Human-readable outcome or status message.",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional free-form context forwarded to callers.",
    )
