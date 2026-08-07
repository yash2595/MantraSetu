"""Domain models for the Rule Engine.

These Pydantic v2 models are intentionally independent of orchestrator
internals and execution machinery so the Rule Engine can evolve without
coupling to downstream services.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import Field

from app.schemas.base import SchemaModel


# ---------------------------------------------------------------------------
# Rule type enumeration
# ---------------------------------------------------------------------------


class RuleType(str, Enum):
    """Classifies which rule category handled a user request.

    Values:
        UNKNOWN:    No rule matched — response is empty, matched=False.
        GREETING:   User sent a greeting (hello, hi, namaste, etc.).
        FAREWELL:   User said goodbye or farewell.
        THANKS:     User expressed gratitude.
        IDENTITY:   User asked who or what Saarthi is.
        HELP:       User asked for help or what Saarthi can do.
        CAPABILITY: User asked about specific services or features.
    """

    UNKNOWN = "unknown"
    GREETING = "greeting"
    FAREWELL = "farewell"
    THANKS = "thanks"
    IDENTITY = "identity"
    HELP = "help"
    CAPABILITY = "capability"


# ---------------------------------------------------------------------------
# Rule result model
# ---------------------------------------------------------------------------


class RuleResult(SchemaModel):
    """Immutable result produced by the Rule Engine for one user turn.

    The Rule Engine always returns one of these — it never returns ``None``
    and never raises silently on a non-match (unmatched input yields
    ``matched=False`` and ``rule_type=UNKNOWN``).

    Attributes:
        rule_type:  Which rule category handled the request.
        matched:    ``True`` when a rule was found for the input.
        response:   Pre-authored response text to return to the user.
                    Empty string when ``matched`` is ``False``.
        confidence: Match confidence in [0.0, 1.0].
        metadata:   Optional free-form context forwarded to callers.
    """

    rule_type: RuleType = Field(
        ...,
        description="Rule category that handled the request.",
    )
    matched: bool = Field(
        ...,
        description="True when a rule was found for the input.",
    )
    response: str = Field(
        default="",
        description="Pre-authored response text. Empty when matched=False.",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Match confidence in [0.0, 1.0].",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional free-form context forwarded to callers.",
    )
