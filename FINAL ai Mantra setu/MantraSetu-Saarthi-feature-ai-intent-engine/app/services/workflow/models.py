"""Domain models for the Workflow Planner.

These Pydantic v2 models are intentionally independent of orchestrator
internals and execution machinery so the Workflow Planner can evolve
without coupling to downstream services.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import Field

from app.schemas.base import SchemaModel


# ---------------------------------------------------------------------------
# Workflow type enumeration
# ---------------------------------------------------------------------------


class WorkflowType(str, Enum):
    """Identifies the category of workflow that should be executed.

    Values:
        UNKNOWN:        No mapping could be determined for the decision.
        RULE:           A deterministic rule-engine workflow handles the request
                        (e.g. greetings, small-talk).
        KNOWLEDGE:      A knowledge-base / RAG lookup workflow answers the
                        request (e.g. "What is Rudrabhishek Puja?").
        NAVIGATION:     A page / feature navigation workflow is needed
                        (e.g. "Open Panchang").
        BOOKING:        A service-booking workflow must be triggered
                        (e.g. "Book Rudrabhishek Puja in Delhi").
        RECOMMENDATION: A personalised recommendation workflow runs
                        (e.g. "Which puja is best for career growth?").
        AI_REASONING:   A complex AI reasoning workflow is required
                        (e.g. birth-chart interpretation).
        SUPPORT:        A customer-support workflow handles the request.
    """

    UNKNOWN = "unknown"
    RULE = "rule"
    KNOWLEDGE = "knowledge"
    NAVIGATION = "navigation"
    BOOKING = "booking"
    RECOMMENDATION = "recommendation"
    AI_REASONING = "ai_reasoning"
    SUPPORT = "support"


# ---------------------------------------------------------------------------
# Workflow step model
# ---------------------------------------------------------------------------


class WorkflowStep(SchemaModel):
    """A single ordered step within a WorkflowPlan.

    Each step names one downstream service or module that should be invoked
    during execution. Steps are declarative — they describe *what* to do,
    not *how* to do it.

    Attributes:
        name:          Human-readable identifier for this step
                       (e.g. ``"Rule Engine"``, ``"Booking Service"``).
        workflow_type: WorkflowType classification for this step.
        order:         1-based execution order within the parent plan.
        enabled:       Whether this step should be executed; allows individual
                       steps to be disabled without removing them from the plan.
        metadata:      Optional free-form context forwarded to the executor.
    """

    name: str = Field(
        ...,
        description="Human-readable step identifier.",
    )
    workflow_type: WorkflowType = Field(
        ...,
        description="WorkflowType classification for this step.",
    )
    order: int = Field(
        default=1,
        ge=1,
        description="1-based execution order within the parent plan.",
    )
    enabled: bool = Field(
        default=True,
        description="Whether this step should be executed.",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional free-form context forwarded to the executor.",
    )


# ---------------------------------------------------------------------------
# Workflow plan model
# ---------------------------------------------------------------------------


class WorkflowPlan(SchemaModel):
    """Immutable execution plan produced by the Workflow Planner.

    The planner always returns one of these — it never returns ``None``
    and never raises silently. The Execution Engine consumes this plan
    to determine which services to invoke and in what order.

    Attributes:
        workflow_type:           Top-level workflow category for the plan.
        steps:                   Ordered list of WorkflowStep instances to
                                 execute.
        requires_ai:             True when AI reasoning is needed.
        requires_navigation:     True when browser / page navigation is needed.
        requires_rag:            True when a knowledge-base RAG lookup is needed.
        requires_booking:        True when a booking workflow must be triggered.
        requires_recommendation: True when the recommendation engine must run.
        metadata:                Optional free-form context forwarded to the
                                 executor.
    """

    workflow_type: WorkflowType = Field(
        ...,
        description="Top-level workflow category for this plan.",
    )
    steps: list[WorkflowStep] = Field(
        default_factory=list,
        description="Ordered list of workflow steps to execute.",
    )
    requires_ai: bool = Field(
        default=False,
        description="True when AI reasoning is required.",
    )
    requires_navigation: bool = Field(
        default=False,
        description="True when browser / page navigation is required.",
    )
    requires_rag: bool = Field(
        default=False,
        description="True when a knowledge-base RAG lookup is required.",
    )
    requires_booking: bool = Field(
        default=False,
        description="True when a booking workflow must be triggered.",
    )
    requires_recommendation: bool = Field(
        default=False,
        description="True when the recommendation engine must run.",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional free-form context forwarded to the executor.",
    )
