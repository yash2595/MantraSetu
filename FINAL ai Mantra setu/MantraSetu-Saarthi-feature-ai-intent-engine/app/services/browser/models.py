"""Domain models for the Browser Session abstraction.

These Pydantic v2 models define the data contract for browser lifecycle management.
They are intentionally minimal and free of any Playwright, Chromium, or automation
specifics so the Browser Session can evolve — adding persistent contexts, incognito,
cookies, tracing — without changing the public interface.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import Field

from app.schemas.base import SchemaModel


# ---------------------------------------------------------------------------
# Browser state enumeration
# ---------------------------------------------------------------------------


class BrowserState(str, Enum):
    """Lifecycle state of a browser session.

    Values:
        STOPPED:  Session is stopped or has not been started yet.
        STARTING: Session is currently starting up (launching browser).
        READY:    Session is active, ready, and capable of interaction.
        CLOSED:   Session has been intentionally closed.
        FAILED:   Session encountered an unrecoverable error.
    """

    STOPPED = "stopped"
    STARTING = "starting"
    READY = "ready"
    CLOSED = "closed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Browser session result model
# ---------------------------------------------------------------------------


class BrowserSessionResult(SchemaModel):
    """Immutable result produced by Browser Session lifecycle methods.

    The service always returns one of these — it never returns ``None``.

    Attributes:
        success:  ``True`` if the requested lifecycle operation succeeded.
        state:    The current state of the browser session after the operation.
        message:  Human-readable outcome or status message.
        metadata: Optional free-form context forwarded to callers.
    """

    success: bool = Field(
        ...,
        description="True if the lifecycle operation succeeded.",
    )
    state: BrowserState = Field(
        default=BrowserState.STOPPED,
        description="Current state of the browser session.",
    )
    message: str = Field(
        default="",
        description="Human-readable outcome or status message.",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional free-form context forwarded to callers.",
    )
