"""Domain models for the Browser Command Executor abstraction."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field

from app.schemas.base import SchemaModel


class BrowserCommandStatus(str, Enum):
    """Execution status of a browser command."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class BrowserCommandRequest(SchemaModel):
    """Request to execute a browser command."""

    command: str = Field(..., description="The command to execute.")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Parameters for the command."
    )


class BrowserCommandResult(SchemaModel):
    """Result of a browser command execution."""

    success: bool = Field(..., description="True if the command succeeded.")
    status: BrowserCommandStatus = Field(..., description="Current status of the command.")
    command: str = Field(..., description="The command that was executed.")
    message: str = Field(default="", description="Outcome message.")
    metadata: dict[str, Any] | None = Field(default=None, description="Optional metadata.")
