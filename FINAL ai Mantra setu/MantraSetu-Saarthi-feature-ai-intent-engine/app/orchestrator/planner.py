"""Orchestrator Planner module for MantraSetu AgentOS.

This module implements the deterministic planner responsible for converting an
ExecutionRequest into an immutable ExecutionPlan.

The planner NEVER executes steps, performs routing, or invokes external systems.
"""

from __future__ import annotations

from app.orchestrator.base import BasePlanner, PlanningError
from app.orchestrator.models import (
    ActionType,
    ExecutionMetadata,
    ExecutionPlan,
    ExecutionRequest,
    ExecutionStep,
)

DEFAULT_TIMEOUT_MS = 30_000
DEFAULT_MAX_RETRIES = 3


class OrchestratorPlanner(BasePlanner):
    """Deterministic planner implementation."""

    async def plan(
        self,
        request: ExecutionRequest,
    ) -> ExecutionPlan:
        """Generate an immutable execution plan."""

        self._validate_request(request)

        steps = self._build_steps(request)

        return self._create_plan(
            request=request,
            steps=steps,
        )

    def _validate_request(
        self,
        request: ExecutionRequest,
    ) -> None:
        """Validate planning request."""

        if request is None:
            raise PlanningError("ExecutionRequest cannot be None.")

        if not request.goal.strip():
            raise PlanningError("Execution goal cannot be empty.")

    def _build_steps(
        self,
        request: ExecutionRequest,
    ) -> tuple[ExecutionStep, ...]:
        """Create semantic execution steps."""

        prepare_step = ExecutionStep(
            action_type=ActionType.WAIT,
            name="Prepare Execution",
            description="Prepare execution context and validate request.",
            parameters=request.parameters,
            timeout_ms=DEFAULT_TIMEOUT_MS,
            max_retries=DEFAULT_MAX_RETRIES,
            metadata=ExecutionMetadata(
                source="planner",
                tags=("prepare",),
            ),
        )

        execute_step = ExecutionStep(
            action_type=ActionType.WAIT,
            name="Execute Requested Operation",
            description=request.goal,
            parameters=request.parameters,
            dependencies=(prepare_step.step_id,),
            timeout_ms=DEFAULT_TIMEOUT_MS,
            max_retries=DEFAULT_MAX_RETRIES,
            metadata=ExecutionMetadata(
                source="planner",
                tags=("execute",),
            ),
        )

        verify_step = ExecutionStep(
            action_type=ActionType.WAIT,
            name="Verify Completion",
            description="Verify execution completed successfully.",
            parameters={},
            dependencies=(execute_step.step_id,),
            timeout_ms=DEFAULT_TIMEOUT_MS,
            max_retries=DEFAULT_MAX_RETRIES,
            metadata=ExecutionMetadata(
                source="planner",
                tags=("verify",),
            ),
        )

        return (
            prepare_step,
            execute_step,
            verify_step,
        )

    def _create_plan(
        self,
        request: ExecutionRequest,
        steps: tuple[ExecutionStep, ...],
    ) -> ExecutionPlan:
        """Create immutable execution plan."""

        return ExecutionPlan(
            request_id=request.request_id,
            steps=steps,
            metadata=ExecutionMetadata(
                source="planner",
                tags=("deterministic",),
            ),
        )