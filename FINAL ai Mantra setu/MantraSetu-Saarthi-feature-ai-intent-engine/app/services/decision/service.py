"""Concrete rule-based Decision Engine implementation.

The RuleBasedDecisionEngine analyses user input through a prioritised sequence
of keyword / pattern rules and returns a DecisionResult that names the
downstream component responsible for execution.

Design constraints:
    - No LLM calls.
    - No Playwright / BrowserService.
    - No navigation execution.
    - No booking execution.
    - No RAG execution.
    - Returns DecisionResult or raises DecisionEngineError — never None.

Future integrations (Intent Service, Workflow Planner, Memory Service, Tool
Registry) can be layered in by subclassing DecisionEngine or by composing this
engine with an adapter, without changing the public interface.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Sequence

from app.orchestrator.models import UserRequest
from app.services.decision.base import DecisionEngine, DecisionEngineError
from app.services.decision.models import DecisionResult, DecisionType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rule definition
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Rule:
    """Single routing rule evaluated against normalised user input.

    Attributes:
        name:       Human-readable label used in log messages.
        decision:   DecisionType to emit when this rule matches.
        patterns:   Sequence of compiled regex patterns; the rule matches if
                    *any* pattern has a hit in the input string.
        confidence: Confidence score assigned to this rule's decision.
        flags:      Keyword arguments forwarded directly to DecisionResult
                    (e.g. ``requires_booking=True``).
    """

    name: str
    decision: DecisionType
    patterns: Sequence[re.Pattern[str]]
    confidence: float = 1.0
    flags: dict[str, bool] = field(default_factory=dict)

    def matches(self, text: str) -> bool:
        """Return True if any pattern matches *text*."""
        return any(p.search(text) for p in self.patterns)


# ---------------------------------------------------------------------------
# Pattern helpers
# ---------------------------------------------------------------------------


def _compile(*raw: str) -> list[re.Pattern[str]]:
    """Compile *raw* strings into case-insensitive regex patterns."""
    return [re.compile(r, re.IGNORECASE) for r in raw]


# ---------------------------------------------------------------------------
# Ordered rule table
# ---------------------------------------------------------------------------
# Rules are evaluated top-to-bottom; the first match wins.
# Add, remove, or reorder rules here without touching any other module.

_RULES: list[_Rule] = [
    # ------------------------------------------------------------------
    # BOOKING — high specificity, must come before NAVIGATION / KNOWLEDGE
    # ------------------------------------------------------------------
    _Rule(
        name="booking",
        decision=DecisionType.BOOKING,
        patterns=_compile(
            r"\bbook\b",
            r"\bschedule\b",
            r"\breserve\b",
            r"\bregister\b.*\bpuja\b",
            r"\bpuja\b.*\bbook\b",
            r"\bappointment\b",
        ),
        confidence=0.95,
        flags={"requires_booking": True},
    ),
    # ------------------------------------------------------------------
    # NAVIGATION — open / go to / show a page
    # ------------------------------------------------------------------
    _Rule(
        name="navigation",
        decision=DecisionType.NAVIGATION,
        patterns=_compile(
            r"\bopen\b",
            r"\bgo to\b",
            r"\bnavigate\b",
            r"\bshow me\b",
            r"\btake me to\b",
            r"\blaunch\b",
            r"\bvisit\b",
        ),
        confidence=0.90,
        flags={"requires_navigation": True},
    ),
    # ------------------------------------------------------------------
    # AI_REASONING — complex analysis / multi-step reasoning
    # (must precede RECOMMENDATION so "analyze … suggest" routes correctly)
    # ------------------------------------------------------------------
    _Rule(
        name="ai_reasoning",
        decision=DecisionType.AI_REASONING,
        patterns=_compile(
            r"\banalyze\b",
            r"\banalyse\b",
            r"\bbirth.?chart\b",
            r"\bkundali\b",
            r"\bpredic\b",
            r"\bforecast\b",
            r"\binterpret\b",
            r"\bexplain.*detail\b",
            r"\bcompare\b",
            r"\bbest time\b",
        ),
        confidence=0.85,
        flags={"requires_ai": True},
    ),
    # ------------------------------------------------------------------
    # RECOMMENDATION — best / suggest / recommend
    # ------------------------------------------------------------------
    _Rule(
        name="recommendation",
        decision=DecisionType.RECOMMENDATION,
        patterns=_compile(
            r"\bbest\b.*\bfor\b",
            r"\bsuggest\b",
            r"\brecommend\b",
            r"\bwhich\b.*\bpuja\b",
            r"\bwhich\b.*\btemple\b",
            r"\bwhich\b.*\bservice\b",
            r"\badvise\b",
        ),
        confidence=0.85,
        flags={"requires_recommendation": True},
    ),

    # ------------------------------------------------------------------
    # KNOWLEDGE — informational FAQ / "what is"
    # ------------------------------------------------------------------
    _Rule(
        name="knowledge",
        decision=DecisionType.KNOWLEDGE,
        patterns=_compile(
            r"\bwhat is\b",
            r"\bwhat are\b",
            r"\bhow (to|do|does|can)\b",
            r"\bwhy (is|are|do|does)\b",
            r"\btell me about\b",
            r"\bexplain\b",
            r"\bdescribe\b",
            r"\bmeaning of\b",
            r"\bdifference between\b",
        ),
        confidence=0.80,
        flags={"requires_rag": True},
    ),
    # ------------------------------------------------------------------
    # SUPPORT — help, issue, problem
    # ------------------------------------------------------------------
    _Rule(
        name="support",
        decision=DecisionType.SUPPORT,
        patterns=_compile(
            r"\bhelp\b",
            r"\bissue\b",
            r"\bproblem\b",
            r"\bcomplaint\b",
            r"\bsupport\b",
            r"\bcontact\b",
            r"\brefund\b",
            r"\bcancel\b",
        ),
        confidence=0.80,
    ),
    # ------------------------------------------------------------------
    # RULE_ENGINE — greetings / small-talk (lowest specificity)
    # ------------------------------------------------------------------
    _Rule(
        name="rule_engine",
        decision=DecisionType.RULE_ENGINE,
        patterns=_compile(
            r"^\s*(hi|hello|hey|namaste|jai|greetings|good\s+(morning|afternoon|evening|night))\b",
            r"\bthank\b",
            r"\bthanks\b",
            r"\bbye\b",
            r"\bgoodbye\b",
            r"\bhow are you\b",
        ),
        confidence=0.90,
    ),
]


# ---------------------------------------------------------------------------
# Concrete engine
# ---------------------------------------------------------------------------


class RuleBasedDecisionEngine(DecisionEngine):
    """Production rule-based Decision Engine.

    Evaluates a fixed, ordered set of keyword / regex rules against
    normalised user input and returns the first matching ``DecisionResult``.
    Falls back to ``DecisionType.UNKNOWN`` when no rule matches.

    This implementation contains **no** LLM calls, browser automation, RAG
    lookups, navigation, booking, or recommendation logic. It is a pure
    routing layer.

    Future extensions:
        Override or compose this class to inject an IntentService, a
        WorkflowPlanner, a MemoryService, a ToolRegistry, or any other
        component without changing the ``DecisionEngine`` interface.
    """

    def __init__(self, rules: list[_Rule] | None = None) -> None:
        """Initialise with an optional custom rule list.

        Args:
            rules: Ordered list of ``_Rule`` instances to evaluate. If
                   ``None``, the module-level ``_RULES`` table is used.
        """
        self._rules = rules if rules is not None else _RULES

    async def decide(self, user_request: UserRequest) -> DecisionResult:
        """Evaluate *user_request* against the rule table and return a routing decision.

        Rule evaluation uses ``user_request.user_input``. The full
        ``UserRequest`` object is available for future use of session context,
        metadata, memory, or conversation history.

        Args:
            user_request: Domain model for the current user turn.

        Returns:
            DecisionResult: Immutable routing decision. Never ``None``.

        Raises:
            DecisionEngineError: If ``user_input`` is missing or blank.
        """
        raw_input = user_request.user_input
        if not isinstance(raw_input, str) or not raw_input.strip():
            raise DecisionEngineError(
                "user_request.user_input must be a non-empty string."
            )

        # Pre-processing: strip surrounding whitespace and collapse internal runs
        normalised = " ".join(raw_input.split())

        logger.info(
            "Decision started | session_id=%s input_length=%d input_preview=%.80r",
            user_request.session_id,
            len(normalised),
            normalised,
        )

        t_start = time.monotonic()

        for rule in self._rules:
            if rule.matches(normalised):
                elapsed_ms = (time.monotonic() - t_start) * 1000
                result = DecisionResult(
                    decision=rule.decision,
                    confidence=rule.confidence,
                    reason=f"Matched rule '{rule.name}'.",
                    **rule.flags,
                )
                logger.info(
                    "Decision selected | matched_rule=%s decision=%s "
                    "confidence=%.2f reason=%r processing_time_ms=%.2f",
                    rule.name,
                    result.decision.value,
                    result.confidence,
                    result.reason,
                    elapsed_ms,
                )
                logger.info(
                    "Decision completed | decision=%s processing_time_ms=%.2f",
                    result.decision.value,
                    elapsed_ms,
                )
                return result

        # Fallback — no rule matched
        elapsed_ms = (time.monotonic() - t_start) * 1000
        result = DecisionResult(
            decision=DecisionType.UNKNOWN,
            confidence=0.0,
            reason="No routing rule matched the input.",
        )
        logger.info(
            "Decision completed | matched_rule=none decision=%s "
            "confidence=%.2f reason=%r processing_time_ms=%.2f",
            result.decision.value,
            result.confidence,
            result.reason,
            elapsed_ms,
        )
        return result

