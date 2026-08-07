"""Tool calling schemas shared by planner, LLM, and API layers."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from app.schemas.base import SchemaModel


class ToolCallStatus(StrEnum):
    """Lifecycle state for a tool call."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ToolResultStatus(StrEnum):
    """Outcome state for a tool execution."""

    SUCCESS = "success"
    FAILURE = "failure"


class ToolCall(SchemaModel):
    """Structured instruction to execute a tool.

    The schema stays generic so planner logic can describe any external action
    without hardcoding provider or transport details.
    """

    call_id: UUID = Field(default_factory=uuid4, description="Unique identifier for the call.")
    tool_name: str = Field(min_length=1, description="Canonical tool name.")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Tool input arguments.")
    status: ToolCallStatus = Field(default=ToolCallStatus.PENDING, description="Current call status.")
    timeout_seconds: float | None = Field(default=None, gt=0, description="Optional per-call timeout.")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the tool call was created.",
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional tool call metadata.")


class ToolResult(SchemaModel):
    """Structured output returned from a tool execution."""

    call_id: UUID = Field(description="Identifier of the originating tool call.")
    tool_name: str = Field(min_length=1, description="Canonical tool name.")
    status: ToolResultStatus = Field(default=ToolResultStatus.SUCCESS, description="Execution outcome.")
    payload: dict[str, Any] | list[Any] | str | int | float | bool | None = Field(
        default=None,
        description="Returned tool output in either structured or scalar form.",
    )
    error_message: str | None = Field(default=None, description="Human-readable error if execution failed.")
    duration_ms: int | None = Field(default=None, ge=0, description="Execution duration in milliseconds.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional tool result metadata.")
