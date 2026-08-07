"""Domain models for the Browser Context abstraction.

These Pydantic v2 models define the data contract for browser context management.
They are intentionally minimal and free of any Playwright, cookies, or authentication
specifics so the Browser Context can evolve — adding persistent contexts, incognito,
and storage state — without changing the public interface.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import Field

from app.schemas.base import SchemaModel


# ---------------------------------------------------------------------------
# Context state enumeration
# ---------------------------------------------------------------------------


class ContextState(str, Enum):
    """Lifecycle state of a browser context.

    Values:
        NOT_CREATED: Context has not been created yet or no longer exists.
        READY:       Context is created and ready for use.
        CLOSED:      Context has been intentionally closed.
        FAILED:      Context encountered an unrecoverable error.
    """

    NOT_CREATED = "not_created"
    READY = "ready"
    CLOSED = "closed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Browser context result model
# ---------------------------------------------------------------------------


class BrowserContextResult(SchemaModel):
    """Immutable result produced by Browser Context lifecycle methods.

    The service always returns one of these — it never returns ``None``.

    Attributes:
        success:    ``True`` if the requested lifecycle operation succeeded.
        state:      The current state of the browser context after the operation.
        context_id: Optional identifier for the context instance.
        message:    Human-readable outcome or status message.
        metadata:   Optional free-form context forwarded to callers.
    """

    success: bool = Field(
        ...,
        description="True if the lifecycle operation succeeded.",
    )
    state: ContextState = Field(
        default=ContextState.NOT_CREATED,
        description="Current state of the browser context.",
    )
    context_id: Optional[str] = Field(
        default=None,
        description="Optional identifier for the context instance.",
    )
    message: str = Field(
        default="",
        description="Human-readable outcome or status message.",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional free-form context forwarded to callers.",
    )
