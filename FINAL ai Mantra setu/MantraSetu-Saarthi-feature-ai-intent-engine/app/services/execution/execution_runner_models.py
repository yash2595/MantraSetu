"""Domain models for the Execution Plan Runner abstraction."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from app.schemas.base import SchemaModel


class ExecutionStatus(str, Enum):
    """Execution status of an execution plan."""

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ExecutionResult(SchemaModel):
    """Result of an execution plan run."""

    success: bool = Field(..., description="True if all steps succeeded.")
    status: ExecutionStatus = Field(..., description="Current status of the execution.")
    executed_steps: int = Field(..., description="Number of steps that were executed.")
    failed_step: str | None = Field(default=None, description="Name of the step that failed, if any.")
    error_message: str | None = Field(default=None, description="Outcome or error message.")
    execution_time_ms: float = Field(..., description="Total execution time in milliseconds.")
    started_at: datetime | None = Field(default=None, description="When execution started.")
    completed_at: datetime | None = Field(default=None, description="When execution completed.")
