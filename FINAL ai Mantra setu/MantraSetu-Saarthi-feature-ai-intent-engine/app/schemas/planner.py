"""Planner schemas for orchestration and execution planning."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from app.schemas.base import SchemaModel
from app.schemas.context import ConversationContext, Entity, Intent, NavigationState
from app.schemas.tools import ToolCall


class PlannerStepStatus(StrEnum):
    """Lifecycle status for an individual planning step."""

    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class PlannerStatus(StrEnum):
    """High-level planner execution state."""

    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


class PlannerStep(SchemaModel):
    """A single executable unit produced by the planner.

    Steps are intentionally generic so the same structure can represent
    navigation flows, booking orchestration, memory lookups, or tool usage.
    """

    step_id: UUID = Field(default_factory=uuid4, description="Unique identifier for the step.")
    name: str = Field(min_length=1, description="Human-readable step name.")
    order: int = Field(default=0, ge=0, description="Zero-based order within the plan.")
    status: PlannerStepStatus = Field(default=PlannerStepStatus.PENDING, description="Current step status.")
    instructions: str = Field(min_length=1, description="What this step should accomplish.")
    input_entities: list[Entity] = Field(default_factory=list, description="Entities required by this step.")
    output_entities: list[Entity] = Field(default_factory=list, description="Entities produced by this step.")
    tool_calls: list[ToolCall] = Field(default_factory=list, description="Tool calls attached to this step.")
    depends_on: list[UUID] = Field(default_factory=list, description="Steps that must complete first.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional step metadata.")


class PlannerResponse(SchemaModel):
    """Planner output that drives downstream execution.

    The planner response acts as the orchestration contract between intent
    resolution, navigation, tool calling, memory, and the final AI response.
    """

    plan_id: UUID = Field(default_factory=uuid4, description="Unique identifier for the plan.")
    status: PlannerStatus = Field(default=PlannerStatus.DRAFT, description="Current plan status.")
    intent: Intent | None = Field(default=None, description="Intent that produced the plan.")
    steps: list[PlannerStep] = Field(default_factory=list, description="Ordered execution steps.")
    active_step_id: UUID | None = Field(default=None, description="Identifier of the currently active step.")
    navigation_state: NavigationState | None = Field(default=None, description="Navigation state for the plan.")
    context: ConversationContext | None = Field(default=None, description="Conversation context used to create the plan.")
    tool_calls: list[ToolCall] = Field(default_factory=list, description="All tool calls generated for the plan.")
    completed_entities: list[Entity] = Field(default_factory=list, description="Entities resolved during planning.")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the plan response was created.",
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional planner metadata.")

    @model_validator(mode="after")
    def validate_active_step(self) -> "PlannerResponse":
        """Ensure the active step, when provided, is part of the plan."""
        if self.active_step_id is not None and self.steps:
            step_ids = {step.step_id for step in self.steps}
            if self.active_step_id not in step_ids:
                raise ValueError("active_step_id must reference one of the provided steps")
        return self
