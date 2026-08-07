"""Domain models for the Browser Navigation abstraction.

These Pydantic v2 models define the data contract for browser navigation.
They isolate the navigation logic from the underlying engine backend.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import Field

from app.schemas.base import SchemaModel


class NavigationState(str, Enum):
    """Execution state of a browser navigation command.

    Values:
        IDLE:      Navigation has not started or is disconnected.
        RUNNING:   Navigation is currently in progress.
        COMPLETED: Navigation completed successfully.
        FAILED:    Navigation failed during execution.
    """
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BrowserNavigationResult(SchemaModel):
    """Immutable result produced by Browser Navigation methods.

    The service always returns one of these — it never returns ``None``.

    Attributes:
        success:  ``True`` if the requested navigation succeeded.
        state:    The current state of the navigation.
        message:  Human-readable outcome or status message.
        url:      The resulting URL if applicable.
        metadata: Optional free-form context forwarded to callers.
    """

    success: bool = Field(
        ...,
        description="True if the navigation succeeded.",
    )
    state: NavigationState = Field(
        default=NavigationState.IDLE,
        description="Current state of the navigation.",
    )
    message: str = Field(
        default="",
        description="Human-readable outcome or status message.",
    )
    url: Optional[str] = Field(
        default=None,
        description="The resulting URL if applicable.",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional free-form context forwarded to callers.",
    )
