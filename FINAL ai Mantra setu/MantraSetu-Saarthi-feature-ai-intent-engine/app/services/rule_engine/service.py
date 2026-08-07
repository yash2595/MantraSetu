"""Concrete Rule Engine implementation.

DefaultRuleEngine evaluates a ``UserRequest`` against an ordered set of
deterministic regex rules and returns a ``RuleResult``.

Design constraints:
    - No LLM calls.
    - No Playwright / BrowserService.
    - No navigation, booking, RAG, or recommendation.
    - Never modifies the incoming ``UserRequest``.
    - Returns ``RuleResult`` or raises ``RuleEngineError`` — never None.

Future extensions:
    Subclass ``RuleEngine`` or compose ``DefaultRuleEngine`` with adapters to
    add festival greetings, dynamic responses, localisation (Hindi/Hinglish),
    or regional personalisation without touching the public interface.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Sequence

from app.orchestrator.models import UserRequest
from app.services.rule_engine.base import RuleEngine, RuleEngineError
from app.services.rule_engine.models import RuleResult, RuleType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rule definition
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Rule:
    """Single deterministic rule evaluated against normalised user input.

    Attributes:
        name:       Human-readable label used in log messages.
        rule_type:  ``RuleType`` to emit when this rule matches.
        patterns:   Compiled regex patterns; the rule matches if *any* hits.
        response:   Pre-authored response text returned to the caller.
        confidence: Confidence score assigned to this rule's match.
    """

    name: str
    rule_type: RuleType
    patterns: Sequence[re.Pattern[str]]
    response: str
    confidence: float = 1.0

    def matches(self, text: str) -> bool:
        """Return ``True`` if any pattern matches *text*."""
        return any(p.search(text) for p in self.patterns)


# ---------------------------------------------------------------------------
# Pattern helpers
# ---------------------------------------------------------------------------


def _compile(*raw: str) -> list[re.Pattern[str]]:
    """Compile *raw* strings into case-insensitive regex patterns."""
    return [re.compile(r, re.IGNORECASE) for r in raw]


# ---------------------------------------------------------------------------
# Canned responses
# ---------------------------------------------------------------------------

_GREETING_RESPONSE = (
    "Hello! I'm Saarthi, your AI spiritual assistant. "
    "How can I assist you today?"
)

_FAREWELL_RESPONSE = "Goodbye! Have a peaceful day. Jai Shri Ram! 🙏"

_THANKS_RESPONSE = "You're welcome! Is there anything else I can help you with?"

_IDENTITY_RESPONSE = (
    "I am Saarthi, your AI spiritual assistant powered by MantraSetu. "
    "I can help you explore pujas, temples, spiritual services, and more."
)

_HELP_RESPONSE = (
    "I'm here to help! Here's what I can do:\n"
    "• Answer questions about pujas and spiritual services\n"
    "• Help you book a puja or ritual\n"
    "• Navigate to temple pages and schedules\n"
    "• Recommend the right puja for your needs\n"
    "• Provide AI-powered spiritual guidance\n\n"
    "Just ask me anything!"
)

_CAPABILITY_RESPONSE = (
    "MantraSetu Saarthi supports the following services:\n"
    "• Puja Booking — schedule rituals at home or temple\n"
    "• Puja Information — learn about any puja or ritual\n"
    "• Temple Navigation — find and visit temple pages\n"
    "• Personalised Recommendations — get the right puja for your goal\n"
    "• AI Spiritual Guidance — birth chart analysis, auspicious timing\n"
    "• Customer Support — help with bookings and enquiries"
)


# ---------------------------------------------------------------------------
# Ordered rule table
# ---------------------------------------------------------------------------
# Rules are evaluated top-to-bottom; the first match wins.
# Add new rules here without touching any other module.

_RULES: list[_Rule] = [
    # ------------------------------------------------------------------
    # GREETING
    # ------------------------------------------------------------------
    _Rule(
        name="greeting",
        rule_type=RuleType.GREETING,
        patterns=_compile(
            r"^\s*(hi|hello|hey|namaste|jai|pranam|greetings)\b",
            r"\bgood\s+(morning|afternoon|evening|night)\b",
            r"^\s*hii+\s*$",
            r"^\s*heyyy*\s*$",
        ),
        response=_GREETING_RESPONSE,
        confidence=0.95,
    ),
    # ------------------------------------------------------------------
    # FAREWELL
    # ------------------------------------------------------------------
    _Rule(
        name="farewell",
        rule_type=RuleType.FAREWELL,
        patterns=_compile(
            r"\bbye\b",
            r"\bgoodbye\b",
            r"\bsee\s+you\b",
            r"\btake\s+care\b",
            r"\buntil\s+next\s+time\b",
            r"\balvida\b",
        ),
        response=_FAREWELL_RESPONSE,
        confidence=0.95,
    ),
    # ------------------------------------------------------------------
    # THANKS
    # ------------------------------------------------------------------
    _Rule(
        name="thanks",
        rule_type=RuleType.THANKS,
        patterns=_compile(
            r"\bthank\s+you\b",
            r"\bthanks\b",
            r"\bthank\s+u\b",
            r"\bdhanyawad\b",
            r"\bshukriya\b",
        ),
        response=_THANKS_RESPONSE,
        confidence=0.95,
    ),
    # ------------------------------------------------------------------
    # IDENTITY
    # ------------------------------------------------------------------
    _Rule(
        name="identity",
        rule_type=RuleType.IDENTITY,
        patterns=_compile(
            r"\bwho\s+are\s+you\b",
            r"\bwhat\s+are\s+you\b",
            r"\btell\s+me\s+about\s+yourself\b",
            r"\byour\s+name\b",
            r"\bintroduce\s+yourself\b",
            r"\baap\s+kaun\s+hain\b",
        ),
        response=_IDENTITY_RESPONSE,
        confidence=0.95,
    ),
    # ------------------------------------------------------------------
    # CAPABILITY — must precede HELP so "what services" routes here
    # ------------------------------------------------------------------
    _Rule(
        name="capability",
        rule_type=RuleType.CAPABILITY,
        patterns=_compile(
            r"\bwhat\s+services\b",
            r"\bwhat\s+can\s+you\s+offer\b",
            r"\bwhat\s+do\s+you\s+offer\b",
            r"\blist\s+(of\s+)?features\b",
            r"\bfeatures\b",
            r"\bcapabilit(y|ies)\b",
            r"\bservices\s+available\b",
        ),
        response=_CAPABILITY_RESPONSE,
        confidence=0.90,
    ),
    # ------------------------------------------------------------------
    # HELP
    # ------------------------------------------------------------------
    _Rule(
        name="help",
        rule_type=RuleType.HELP,
        patterns=_compile(
            r"^\s*help\s*$",
            r"\bwhat\s+can\s+you\s+do\b",
            r"\bhow\s+can\s+you\s+help\b",
            r"\bwhat\s+do\s+you\s+do\b",
            r"\bhelp\s+me\b",
            r"\bi\s+need\s+help\b",
        ),
        response=_HELP_RESPONSE,
        confidence=0.90,
    ),
]


# ---------------------------------------------------------------------------
# Concrete engine
# ---------------------------------------------------------------------------


class DefaultRuleEngine(RuleEngine):
    """Production rule engine using an ordered, static rule table.

    Normalises input (strip whitespace, collapse runs), evaluates rules
    top-to-bottom, and returns the first matching ``RuleResult``.
    Returns ``RuleResult(matched=False, rule_type=UNKNOWN)`` when no rule
    matches — never raises on a non-match.

    This implementation contains **no** LLM calls, browser automation, RAG
    lookups, navigation, booking, or recommendation logic. It is a pure
    deterministic routing layer.

    Future extensions:
        Override or compose this class to add festival greetings, dynamic
        responses, localisation, or Hindi/Hinglish support without changing
        the ``RuleEngine`` interface.
    """

    def __init__(self, rules: list[_Rule] | None = None) -> None:
        """Initialise with an optional custom rule list.

        Args:
            rules: Ordered list of ``_Rule`` instances to evaluate. If
                   ``None``, the module-level ``_RULES`` table is used.
        """
        self._rules: list[_Rule] = rules if rules is not None else _RULES

    async def process(self, request: UserRequest) -> RuleResult:
        """Evaluate *request* against the rule table and return a result.

        Args:
            request: ``UserRequest`` domain model for the current user turn.

        Returns:
            RuleResult: Immutable match result. Never ``None``.

        Raises:
            RuleEngineError: If ``request`` is invalid or ``user_input`` is
                             missing or blank.
        """
        if not isinstance(request, UserRequest):
            raise RuleEngineError("request must be a UserRequest instance.")

        raw_input = request.user_input
        if not isinstance(raw_input, str) or not raw_input.strip():
            raise RuleEngineError(
                "request.user_input must be a non-empty string."
            )

        # Normalise: strip surrounding whitespace, collapse internal runs
        normalised = " ".join(raw_input.split())

        logger.info(
            "Rule processing started | session_id=%s input_length=%d "
            "input_preview=%.80r",
            request.session_id,
            len(normalised),
            normalised,
        )

        t_start = time.monotonic()

        for rule in self._rules:
            if rule.matches(normalised):
                elapsed_ms = (time.monotonic() - t_start) * 1000
                result = RuleResult(
                    rule_type=rule.rule_type,
                    matched=True,
                    response=rule.response,
                    confidence=rule.confidence,
                )
                logger.info(
                    "Rule matched | rule=%s rule_type=%s confidence=%.2f "
                    "processing_time_ms=%.2f",
                    rule.name,
                    result.rule_type.value,
                    result.confidence,
                    elapsed_ms,
                )
                logger.info(
                    "Rule processing completed | matched=True rule_type=%s "
                    "processing_time_ms=%.2f",
                    result.rule_type.value,
                    elapsed_ms,
                )
                return result

        # No rule matched — return a valid UNKNOWN result, never raise
        elapsed_ms = (time.monotonic() - t_start) * 1000
        result = RuleResult(
            rule_type=RuleType.UNKNOWN,
            matched=False,
            response="",
            confidence=0.0,
        )
        logger.info(
            "Rule processing completed | matched=False rule_type=%s "
            "processing_time_ms=%.2f",
            result.rule_type.value,
            elapsed_ms,
        )
        return result
