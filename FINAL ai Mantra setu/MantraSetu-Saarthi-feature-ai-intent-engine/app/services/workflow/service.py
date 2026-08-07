"""Concrete Workflow Planner implementation.

DefaultWorkflowPlanner converts a DecisionResult into a WorkflowPlan using a
simple, static mapping table. It is the bridge between the Decision Engine and
the Execution Engine.

Design constraints:
    - No LLM calls.
    - No Playwright / BrowserService.
    - No navigation execution.
    - No booking execution.
    - No RAG execution.
    - No recommendation execution.
    - Returns WorkflowPlan or raises WorkflowPlannerError — never None.

Future extensions:
    Subclass WorkflowPlanner or compose DefaultWorkflowPlanner with adapters to
    add conditional workflows, multi-step plans, fallback/retry strategies,
    human-approval gates, Tool Registry, or Memory Service integration without
    touching the public interface.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Sequence

from app.services.decision.models import DecisionResult, DecisionType
from app.services.workflow.base import WorkflowPlanner, WorkflowPlannerError
from app.services.workflow.models import WorkflowPlan, WorkflowStep, WorkflowType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mapping entry
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Mapping:
    """Static decision-to-workflow mapping entry.

    Attributes:
        decision_type:           The DecisionType this entry handles.
        workflow_type:           The WorkflowType to assign to the plan.
        step_name:               Human-readable name for the single workflow step.
        requires_ai:             Forwarded to WorkflowPlan.requires_ai.
        requires_navigation:     Forwarded to WorkflowPlan.requires_navigation.
        requires_rag:            Forwarded to WorkflowPlan.requires_rag.
        requires_booking:        Forwarded to WorkflowPlan.requires_booking.
        requires_recommendation: Forwarded to WorkflowPlan.requires_recommendation.
    """

    decision_type: DecisionType
    workflow_type: WorkflowType
    step_name: str
    requires_ai: bool = False
    requires_navigation: bool = False
    requires_rag: bool = False
    requires_booking: bool = False
    requires_recommendation: bool = False


# ---------------------------------------------------------------------------
# Static mapping table
# ---------------------------------------------------------------------------
# Each DecisionType maps to exactly one WorkflowType and one named step.
# Future multi-step plans can extend this table without changing the planner.

_MAPPINGS: dict[DecisionType, _Mapping] = {
    m.decision_type: m
    for m in [
        _Mapping(
            decision_type=DecisionType.RULE_ENGINE,
            workflow_type=WorkflowType.RULE,
            step_name="Rule Engine",
        ),
        _Mapping(
            decision_type=DecisionType.KNOWLEDGE,
            workflow_type=WorkflowType.KNOWLEDGE,
            step_name="Knowledge Service",
            requires_rag=True,
        ),
        _Mapping(
            decision_type=DecisionType.NAVIGATION,
            workflow_type=WorkflowType.NAVIGATION,
            step_name="Navigation Service",
            requires_navigation=True,
        ),
        _Mapping(
            decision_type=DecisionType.BOOKING,
            workflow_type=WorkflowType.BOOKING,
            step_name="Booking Service",
            requires_booking=True,
        ),
        _Mapping(
            decision_type=DecisionType.RECOMMENDATION,
            workflow_type=WorkflowType.RECOMMENDATION,
            step_name="Recommendation Engine",
            requires_recommendation=True,
        ),
        _Mapping(
            decision_type=DecisionType.AI_REASONING,
            workflow_type=WorkflowType.AI_REASONING,
            step_name="AI Reasoning Service",
            requires_ai=True,
        ),
        _Mapping(
            decision_type=DecisionType.SUPPORT,
            workflow_type=WorkflowType.SUPPORT,
            step_name="Support Service",
        ),
        _Mapping(
            decision_type=DecisionType.UNKNOWN,
            workflow_type=WorkflowType.UNKNOWN,
            step_name="",  # no step for UNKNOWN
        ),
    ]
}


# ---------------------------------------------------------------------------
# Concrete planner
# ---------------------------------------------------------------------------


class DefaultWorkflowPlanner(WorkflowPlanner):
    """Production workflow planner using a static decision-to-workflow mapping.

    Maps each ``DecisionType`` to a single-step ``WorkflowPlan`` using the
    ``_MAPPINGS`` table. Falls back to ``WorkflowType.UNKNOWN`` with an empty
    step list when no mapping exists for an unrecognised decision type.

    This implementation contains **no** LLM calls, browser automation, RAG
    lookups, navigation, booking, or recommendation logic. It is a pure
    planning layer.

    Future extensions:
        Override or compose this class to support conditional workflows,
        multi-step plans, fallback strategies, retry policies, or human-approval
        gates without changing the ``WorkflowPlanner`` interface.
    """

    def __init__(
        self,
        mappings: dict[DecisionType, _Mapping] | None = None,
    ) -> None:
        """Initialise with an optional custom mapping table.

        Args:
            mappings: Decision-to-workflow mapping dictionary. If ``None``,
                      the module-level ``_MAPPINGS`` table is used.
        """
        self._mappings: dict[DecisionType, _Mapping] = (
            mappings if mappings is not None else _MAPPINGS
        )

    async def create_plan(self, decision: DecisionResult) -> WorkflowPlan:
        """Convert *decision* into an executable workflow plan.

        Args:
            decision: ``DecisionResult`` produced by the Decision Engine.

        Returns:
            WorkflowPlan: Immutable plan. Never ``None``.

        Raises:
            WorkflowPlannerError: If *decision* is not a valid ``DecisionResult``.
        """
        if not isinstance(decision, DecisionResult):
            raise WorkflowPlannerError(
                "decision must be a DecisionResult instance."
            )

        logger.info(
            "Workflow planning started | decision=%s confidence=%.2f",
            decision.decision.value,
            decision.confidence,
        )

        t_start = time.monotonic()

        mapping = self._mappings.get(decision.decision)

        if mapping is None:
            # Unrecognised DecisionType — safe fallback
            elapsed_ms = (time.monotonic() - t_start) * 1000
            plan = WorkflowPlan(
                workflow_type=WorkflowType.UNKNOWN,
                steps=[],
                metadata={"reason": f"No mapping for decision '{decision.decision.value}'."},
            )
            logger.warning(
                "Workflow planning completed | workflow=%s steps=0 "
                "planning_time_ms=%.2f reason='No mapping found'",
                plan.workflow_type.value,
                elapsed_ms,
            )
            return plan

        # Build steps — UNKNOWN decision intentionally produces no steps
        steps: list[WorkflowStep] = []
        if mapping.step_name:
            steps.append(
                WorkflowStep(
                    name=mapping.step_name,
                    workflow_type=mapping.workflow_type,
                    order=1,
                    enabled=True,
                )
            )

        plan = WorkflowPlan(
            workflow_type=mapping.workflow_type,
            steps=steps,
            requires_ai=mapping.requires_ai,
            requires_navigation=mapping.requires_navigation,
            requires_rag=mapping.requires_rag,
            requires_booking=mapping.requires_booking,
            requires_recommendation=mapping.requires_recommendation,
            metadata={"decision_reason": decision.reason},
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000

        logger.info(
            "Workflow selected | workflow=%s steps=%d planning_time_ms=%.2f",
            plan.workflow_type.value,
            len(plan.steps),
            elapsed_ms,
        )

        if plan.steps:
            for step in plan.steps:
                logger.info(
                    "Workflow step created | order=%d name=%r workflow=%s enabled=%s",
                    step.order,
                    step.name,
                    step.workflow_type.value,
                    step.enabled,
                )

        logger.info(
            "Workflow planning completed | workflow=%s steps=%d "
            "requires_ai=%s requires_navigation=%s requires_rag=%s "
            "requires_booking=%s requires_recommendation=%s "
            "planning_time_ms=%.2f",
            plan.workflow_type.value,
            len(plan.steps),
            plan.requires_ai,
            plan.requires_navigation,
            plan.requires_rag,
            plan.requires_booking,
            plan.requires_recommendation,
            elapsed_ms,
        )

        return plan
