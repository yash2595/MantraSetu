"""Domain models and schemas for the Agent Core subsystem in MantraSetu AgentOS.

This module defines immutable Pydantic v2 domain models for agent tasks, plans,
execution results, agent contexts, and operational statuses without LLM SDK coupling.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Mapping
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def _utc_now() -> datetime:
    """Return the current timestamp in UTC.

    Returns:
        datetime: Current timezone-aware datetime instance in UTC.
    """
    return datetime.now(timezone.utc)


class BaseAgentModel(BaseModel):
    """Base Pydantic v2 model for immutable Agent domain entities."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )


class AgentStatus(str, Enum):
    """Enumeration of agent task execution lifecycle states."""

    IDLE = "idle"
    THINKING = "thinking"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentTask(BaseAgentModel):
    """Domain model representing an autonomous agent task unit.

    Attributes:
        task_id: Unique agent task identifier UUID.
        user_input: Raw user prompt or instruction input string.
        intent: Optional recognized intent type or classification string.
        status: AgentStatus enum value indicating current state.
        metadata: Immutable key-value metadata mapping.
        created_at: UTC creation timestamp.
    """

    task_id: UUID = Field(
        default_factory=uuid4,
        description="Unique agent task identifier UUID.",
    )
    user_input: str = Field(
        ...,
        description="Raw user prompt or instruction input string.",
    )
    intent: str | None = Field(
        default=None,
        description="Optional recognized intent type or classification string.",
    )
    status: AgentStatus = Field(
        default=AgentStatus.IDLE,
        description="AgentStatus enum value indicating current state.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable key-value metadata mapping.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC creation timestamp.",
    )


class AgentPlan(BaseAgentModel):
    """Domain model representing a multi-step task execution plan.

    Attributes:
        plan_id: Unique plan identifier UUID.
        task_id: Associated AgentTask identifier UUID.
        steps: Immutable tuple of step instruction strings.
        current_step: Zero-based current step index integer.
        metadata: Immutable key-value metadata mapping.
    """

    plan_id: UUID = Field(
        default_factory=uuid4,
        description="Unique plan identifier UUID.",
    )
    task_id: UUID = Field(
        ...,
        description="Associated AgentTask identifier UUID.",
    )
    steps: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Immutable tuple of step instruction strings.",
    )
    current_step: int = Field(
        default=0,
        ge=0,
        description="Zero-based current step index integer.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable key-value metadata mapping.",
    )


class AgentExecutionResult(BaseAgentModel):
    """Domain model capturing the result of an agent task execution.

    Attributes:
        execution_id: Unique execution identifier UUID.
        task_id: Associated AgentTask identifier UUID.
        success: Boolean flag indicating if execution succeeded.
        output: Final response or task output string.
        actions: Immutable tuple of executed action summary strings.
        metadata: Immutable key-value metadata mapping.
    """

    execution_id: UUID = Field(
        default_factory=uuid4,
        description="Unique execution identifier UUID.",
    )
    task_id: UUID = Field(
        ...,
        description="Associated AgentTask identifier UUID.",
    )
    success: bool = Field(
        ...,
        description="Boolean flag indicating if execution succeeded.",
    )
    output: str = Field(
        default="",
        description="Final response or task output string.",
    )
    actions: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Immutable tuple of executed action summary strings.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable key-value metadata mapping.",
    )


class AgentContext(BaseAgentModel):
    """Domain model consolidating complete agent execution context.

    Attributes:
        task_id: Associated AgentTask identifier UUID.
        conversation_id: Optional associated conversation identifier UUID.
        session_id: Optional associated user session identifier UUID.
        rag_context: Immutable RAG retrieval context mapping.
        navigation_context: Immutable navigation context mapping.
        metadata: Immutable key-value metadata mapping.
    """

    task_id: UUID = Field(
        ...,
        description="Associated AgentTask identifier UUID.",
    )
    conversation_id: UUID | None = Field(
        default=None,
        description="Optional associated conversation identifier UUID.",
    )
    session_id: UUID | None = Field(
        default=None,
        description="Optional associated user session identifier UUID.",
    )
    rag_context: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable RAG retrieval context mapping.",
    )
    navigation_context: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable navigation context mapping.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable key-value metadata mapping.",
    )
