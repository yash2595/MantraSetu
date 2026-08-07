"""Domain models for the Execution Engine.

These Pydantic v2 models define the data contract for workflow execution.
They are intentionally minimal and free of any service-specific, browser,
or LLM logic so the Execution Engine can evolve — adding parallel execution,
retry policy, rollback, streaming progress events — without changing the
public interface.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import Field

from app.schemas.base import SchemaModel


# ---------------------------------------------------------------------------
# Execution status enumeration
# ---------------------------------------------------------------------------


class ExecutionStatus(str, Enum):
    """Lifecycle status of a workflow execution.

    Values:
        NOT_EXECUTED: Workflow was received but not executed (placeholder).
        COMPLETED:    Workflow execution completed successfully.
        FAILED:       Workflow execution was attempted and failed.
    """

    NOT_EXECUTED = "not_executed"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Execution result model
# ---------------------------------------------------------------------------


class ExecutionResult(SchemaModel):
    """Immutable result produced by the Execution Engine for one workflow run.

    The engine always returns one of these — it never returns ``None``.
    In the placeholder implementation, ``executed`` is always ``False``.

    Attributes:
        executed:   ``True`` when the workflow was actually dispatched to a
                    downstream service.
        status:     Lifecycle status of this execution.
        message:    Human-readable outcome message. Empty in the placeholder.
        confidence: Execution confidence in [0.0, 1.0].
        metadata:   Optional free-form context forwarded to callers.
    """

    executed: bool = Field(
        ...,
        description="True when the workflow was dispatched to a downstream service.",
    )
    status: ExecutionStatus = Field(
        default=ExecutionStatus.NOT_EXECUTED,
        description="Lifecycle status of this execution.",
    )
    message: str = Field(
        default="",
        description="Human-readable outcome message.",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Execution confidence in [0.0, 1.0].",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional free-form context forwarded to callers.",
    )
