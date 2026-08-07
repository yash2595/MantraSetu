"""Domain models for the Browser Actions abstraction.

These Pydantic v2 models define the data contract for high-level browser actions
such as clicking, typing, scrolling, and waiting. They are intentionally minimal
and free of any Playwright or DOM specifics so the execution backend can be swapped
without changing the public interface.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import Field

from app.schemas.base import SchemaModel


# ---------------------------------------------------------------------------
# Action state enumeration
# ---------------------------------------------------------------------------


class ActionState(str, Enum):
    """Execution state of a browser action.

    Values:
        IDLE:      Action has not started or is a placeholder.
        RUNNING:   Action is currently being executed by the driver.
        COMPLETED: Action completed successfully.
        FAILED:    Action failed during execution.
    """

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Browser action result model
# ---------------------------------------------------------------------------


class BrowserActionResult(SchemaModel):
    """Immutable result produced by Browser Actions methods.

    The service always returns one of these — it never returns ``None``.

    Attributes:
        success:  ``True`` if the requested action succeeded.
        state:    The current state of the browser action after the operation.
        action:   The name of the action performed (e.g., 'click', 'scroll').
        message:  Human-readable outcome or status message.
        metadata: Optional free-form context forwarded to callers.
    """

    success: bool = Field(
        ...,
        description="True if the action succeeded.",
    )
    state: ActionState = Field(
        default=ActionState.IDLE,
        description="Current state of the browser action.",
    )
    action: str = Field(
        ...,
        description="Name of the action performed.",
    )
    message: str = Field(
        default="",
        description="Human-readable outcome or status message.",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional free-form context forwarded to callers.",
    )
