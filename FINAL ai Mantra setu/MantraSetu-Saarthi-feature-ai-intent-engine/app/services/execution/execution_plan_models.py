"""Domain models for the Execution Plan abstraction."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from app.schemas.base import SchemaModel


class ExecutionStep(SchemaModel):
    """An executable step in an execution plan.

    This model acts as a lightweight transport object that specifies a single
    operation to be performed, carrying the name of the target tool and its
    associated parameters.
    """

    tool: str = Field(..., description="The name of the tool to execute.")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Parameters required by the tool."
    )
    description: str | None = Field(
        default=None, description="Optional description of the step."
    )

    @field_validator("tool")
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        """Validate that the tool name is not empty or whitespace.

        Args:
            v: The string value of the tool name to validate.

        Returns:
            The stripped tool name.

        Raises:
            ValueError: If the tool name is empty or consists only of whitespace.
        """
        stripped = v.strip()
        if not stripped:
            raise ValueError("Tool name cannot be empty or whitespace.")
        return stripped


class ExecutionPlan(SchemaModel):
    """An ordered sequence of executable steps.

    This model serves as a lightweight transport mechanism to carry an execution
    plan from the AI Planner layer to the Browser Command Executor. It defines
    exactly what steps need to be executed in sequence without embedding any
    execution or business logic.
    """

    steps: list[ExecutionStep] = Field(
        ..., description="The ordered sequence of steps to execute."
    )

    @field_validator("steps")
    @classmethod
    def validate_steps_not_empty(cls, v: list[ExecutionStep]) -> list[ExecutionStep]:
        """Validate that the plan contains at least one step.

        Args:
            v: The list of execution steps.

        Returns:
            The validated list of steps.

        Raises:
            ValueError: If the steps list is empty.
        """
        if not v:
            raise ValueError("Execution plan must contain at least one step.")
        return v
