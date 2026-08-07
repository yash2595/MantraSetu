"""Default implementation of the Workflow Planner abstraction."""

from __future__ import annotations

import logging
import time

from app.services.browser_intelligence.task_context_models import TaskContext
from app.services.execution.execution_plan_models import ExecutionPlan, ExecutionStep
from app.services.execution.workflow_planner_base import (
    PlannerError,
    WorkflowPlanner,
)

logger = logging.getLogger(__name__)


class DefaultWorkflowPlanner(WorkflowPlanner):
    """A rule-based Sprint 1 planner mapping static intents to execution plans.

    This planner contains no execution logic, no browser coupling, and no AI reasoning.
    It strictly converts a known user intent string into a declarative ExecutionPlan.
    """

    def __init__(self) -> None:
        """Initialize the default workflow planner."""
        pass

    async def plan(self, intent: str, task_context: TaskContext | None = None) -> ExecutionPlan:
        """Convert a user intent into an ordered ExecutionPlan."""
        logger.info("Planner started")

        if intent is None:
            raise PlannerError("Intent cannot be None.")

        intent_stripped = intent.strip()
        if not intent_stripped:
            raise PlannerError("Intent cannot be empty or whitespace.")

        logger.info("Intent received | intent=%s", intent_stripped)
        
        if task_context:
            logger.info("TaskContext received")
            logger.info("Planner summary evaluated")
            
        start_time = time.monotonic()

        intent_lower = intent_stripped.lower()
        steps: list[ExecutionStep] = []

        if intent_lower == "open services page":
            if task_context and task_context.summary.page_url and "/services" in task_context.summary.page_url:
                logger.info("Optimization applied | Already on services page, skipping navigation")
            else:
                steps.append(ExecutionStep(tool="NavigateToPage", parameters={"target": "services_page"}))
        elif intent_lower == "go back":
            steps.append(ExecutionStep(tool="GoBack", parameters={}))
        elif intent_lower == "refresh page":
            steps.append(ExecutionStep(tool="RefreshPage", parameters={}))
        elif intent_lower == "click book button":
            if task_context and (not task_context.summary.has_primary_action or task_context.summary.primary_action_count == 0):
                logger.warning("Optimization applied | No primary action available, skipping click")
            else:
                steps.append(ExecutionStep(tool="ClickPrimaryAction", parameters={"target": "book_button"}))
        elif intent_lower == "fill form":
            if task_context and not task_context.summary.has_input:
                logger.warning("Optimization applied | No input field available, skipping fill")
            else:
                steps.append(ExecutionStep(tool="FillRequiredInputs", parameters={"target": "booking_form"}))
        else:
            raise PlannerError(f"No rule defined for intent: '{intent_stripped}'")

        logger.info("Execution plan finalized")
        plan = ExecutionPlan(steps=steps)

        elapsed_ms = (time.monotonic() - start_time) * 1000
        logger.info(
            "ExecutionPlan generated | steps_count=%d | processing_time_ms=%.2f",
            len(plan.steps),
            elapsed_ms,
        )

        return plan
