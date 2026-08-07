"""Domain models for the Browser Driver abstraction.

These Pydantic v2 models define the low-level data contract for browser engine drivers.
They are intentionally minimal and free of any Playwright, CDP, or Selenium specifics
so the engine backend can be swapped without changing the public interface.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.schemas.base import SchemaModel


# ---------------------------------------------------------------------------
# Driver state enumeration
# ---------------------------------------------------------------------------


class DriverState(str, Enum):
    """Connection state of a browser driver.

    Values:
        DISCONNECTED: Driver is not connected to a browser engine.
        CONNECTED:    Driver is connected and ready to execute commands.
        FAILED:       Driver encountered an unrecoverable error.
    """

    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Infrastructure Models
# ---------------------------------------------------------------------------


class BrowserSessionHandle(BaseModel):
    """Internal infrastructure model holding a specific session's resources.
    
    This object belongs to the BrowserDriver and must NOT be exposed 
    to the domain or BrowserSessionManager.
    """

    session_id: str
    browser: Any = None
    browser_context: Any = None
    browser_page: Any = None


# ---------------------------------------------------------------------------
# Browser driver result model
# ---------------------------------------------------------------------------


class BrowserDriverResult(SchemaModel):
    """Immutable result produced by Browser Driver methods.

    The service always returns one of these — it never returns ``None``.

    Attributes:
        success:  ``True`` if the requested driver operation succeeded.
        state:    The current state of the browser driver after the operation.
        message:  Human-readable outcome or status message.
        metadata: Optional free-form context forwarded to callers.
    """

    success: bool = Field(
        ...,
        description="True if the driver operation succeeded.",
    )
    state: DriverState = Field(
        default=DriverState.DISCONNECTED,
        description="Current state of the browser driver.",
    )
    message: str = Field(
        default="",
        description="Human-readable outcome or status message.",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional free-form context forwarded to callers.",
    )
