"""Domain models for the Decision Engine.

These Pydantic v2 models are intentionally independent of orchestrator
internals so the Decision Engine can evolve without coupling to other
subsystems.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import Field

from app.schemas.base import SchemaModel


# ---------------------------------------------------------------------------
# Decision type enumeration
# ---------------------------------------------------------------------------


class DecisionType(str, Enum):
    """Downstream component that should handle a routed user request.

    Values:
        UNKNOWN:        No routing rule matched; intent is unclear.
        RULE_ENGINE:    Simple deterministic rules can answer the request
                        (e.g. greetings, small-talk, status checks).
        AI_REASONING:   Complex reasoning or multi-step analysis is required
                        (e.g. birth-chart interpretation, comparative analysis).
        KNOWLEDGE:      A knowledge-base / RAG lookup should answer the request
                        (e.g. "What is Rudrabhishek Puja?").
        NAVIGATION:     The user wants to open or navigate to a page or feature
                        (e.g. "Open Panchang").
        BOOKING:        The user wants to book a service or product
                        (e.g. "Book Rudrabhishek Puja in Delhi").
        RECOMMENDATION: The user wants a personalised suggestion
                        (e.g. "Which puja is best for career growth?").
        SUPPORT:        The user needs help, FAQs, or human escalation.
    """

    UNKNOWN = "unknown"
    RULE_ENGINE = "rule_engine"
    AI_REASONING = "ai_reasoning"
    KNOWLEDGE = "knowledge"
    NAVIGATION = "navigation"
    BOOKING = "booking"
    RECOMMENDATION = "recommendation"
    SUPPORT = "support"


# ---------------------------------------------------------------------------
# Decision result model
# ---------------------------------------------------------------------------


class DecisionResult(SchemaModel):
    """Immutable routing decision produced by the Decision Engine.

    The Decision Engine always returns one of these — it never returns
    ``None`` and never raises silently.

    Attributes:
        decision:               Which downstream component should handle the
                                request.
        confidence:             Routing confidence score in [0.0, 1.0].
        reason:                 Human-readable justification for the decision,
                                used for logging and debugging.
        requires_ai:            True when the AI reasoning layer must be
                                involved in execution.
        requires_navigation:    True when browser / page navigation is needed.
        requires_rag:           True when a knowledge-base lookup is needed.
        requires_booking:       True when a booking workflow must be triggered.
        requires_recommendation: True when the recommendation engine must run.
        metadata:               Optional free-form context forwarded to the
                                downstream handler.
    """

    decision: DecisionType = Field(
        ...,
        description="Downstream component that should handle the request.",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Routing confidence score in [0.0, 1.0].",
    )
    reason: str = Field(
        default="",
        description="Human-readable justification for the routing decision.",
    )
    requires_ai: bool = Field(
        default=False,
        description="True when AI reasoning is required for execution.",
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
        description="Optional free-form context forwarded to the downstream handler.",
    )
