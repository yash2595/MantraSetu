"""Multi-Intent Classification & Confidence Scoring Engine v1.0."""

from __future__ import annotations

import logging
import re
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.conversation.conversation_models import DetectedIntent, IntentCategory

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "IntentEngine"
_COMPONENT_VERSION = "1.0.0"


class IntentEngine:
    """Enterprise multi-intent detection engine using pattern matching and keyword semantics."""

    # Intent keyword rules map
    _RULES: list[tuple[str, IntentCategory, str, list[str]]] = [
        (r"\b(book|schedule|reserve|pooja|puja)\b", IntentCategory.BOOKING_PUJA, "BOOKING_PUJA", ["SELECT_DATE", "SELECT_PANDIT"]),
        (r"\b(kundali|horoscope|birth chart|janam kundali)\b", IntentCategory.KUNDALI_INQUIRY, "KUNDALI_INQUIRY", ["PROVIDE_BIRTH_DETAILS"]),
        (r"\b(muhurat|auspicious time|shubh muhurat)\b", IntentCategory.MUHURAT_SEARCH, "MUHURAT_SEARCH", ["SEARCH_DATE"]),
        (r"\b(astrologer|consult|talk to pandit|jyotish)\b", IntentCategory.ASTROLOGER_CONSULT, "ASTROLOGER_CONSULT", ["SELECT_ASTROLOGER"]),
        (r"\b(navigate|go to|open|show|page|screen)\b", IntentCategory.NAVIGATION_COMMAND, "NAVIGATE_PAGE", []),
        (r"\b(cancel|stop|reset|restart|help)\b", IntentCategory.SYSTEM_COMMAND, "SYSTEM_COMMAND", []),
    ]

    def __init__(self) -> None:
        self._lock = RLock()
        self._intents_detected_count = 0

    def detect_intent(self, utterance: str) -> DetectedIntent:
        """Classify primary intent and confidence score from user utterance string."""
        with self._lock:
            self._intents_detected_count += 1
            if not utterance or not utterance.strip():
                return DetectedIntent(intent_name="UNKNOWN", category=IntentCategory.UNKNOWN, confidence=0.0)

            clean_text = utterance.strip().lower()

            for pattern, category, intent_name, sub_intents in self._RULES:
                if re.search(pattern, clean_text, re.IGNORECASE):
                    logger.debug("IntentEngine matched intent '%s' (category: %s)", intent_name, category)
                    return DetectedIntent(
                        intent_name=intent_name,
                        category=category,
                        confidence=0.92,
                        sub_intents=sub_intents,
                        reasoning=f"Matched regex pattern '{pattern}'",
                    )

            # Fallback general inquiry if text is long enough
            if len(clean_text) > 3:
                return DetectedIntent(
                    intent_name="GENERAL_INQUIRY",
                    category=IntentCategory.GENERAL_INQUIRY,
                    confidence=0.65,
                    reasoning="Fallback semantic text length heuristic",
                )

            return DetectedIntent(intent_name="UNKNOWN", category=IntentCategory.UNKNOWN, confidence=0.1)

    def detect_sub_intents(self, utterance: str) -> list[DetectedIntent]:
        """Detect secondary sub-intents in compound user utterances."""
        with self._lock:
            results: list[DetectedIntent] = []
            clean_text = utterance.strip().lower()

            for pattern, category, intent_name, sub_intents in self._RULES:
                if re.search(pattern, clean_text, re.IGNORECASE):
                    results.append(
                        DetectedIntent(
                            intent_name=intent_name,
                            category=category,
                            confidence=0.85,
                            sub_intents=sub_intents,
                            reasoning=f"Matched sub-intent pattern '{pattern}'",
                        )
                    )
            return results

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "intents_detected_count": self._intents_detected_count,
                "registered_rules_count": len(self._RULES),
            }

    def metrics(self) -> dict[str, Any]:
        """Expose metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            details=self.statistics(),
        )
