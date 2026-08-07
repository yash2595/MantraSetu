"""Strategy Selection Engine for Multi-Intent Prioritization & Clarifications v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.conversation.conversation_models import (
    ClarificationStrategy,
    ClarificationType,
    ConfirmationStrategy,
    DetectedIntent,
    IntentCategory,
)

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ConversationStrategyEngine"
_COMPONENT_VERSION = "1.0.0"


class ConversationStrategyEngine:
    """Enterprise strategy engine managing multi-intent prioritization, clarification selection, and confirmation strategies."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._strategies_evaluated_count = 0

    def prioritize_intents(self, detected_intents: list[DetectedIntent]) -> DetectedIntent:
        """Select highest priority intent from a list of candidate detected intents."""
        with self._lock:
            self._strategies_evaluated_count += 1
            if not detected_intents:
                return DetectedIntent(intent_name="UNKNOWN", category=IntentCategory.UNKNOWN, confidence=0.0)

            # Prioritize by category weight then confidence
            category_weights = {
                IntentCategory.SYSTEM_COMMAND: 10,
                IntentCategory.NAVIGATION_COMMAND: 9,
                IntentCategory.BOOKING_PUJA: 8,
                IntentCategory.KUNDALI_INQUIRY: 7,
                IntentCategory.MUHURAT_SEARCH: 6,
                IntentCategory.ASTROLOGER_CONSULT: 5,
                IntentCategory.GENERAL_INQUIRY: 4,
                IntentCategory.UNKNOWN: 0,
            }

            sorted_intents = sorted(
                detected_intents,
                key=lambda i: (category_weights.get(i.category, 0), i.confidence),
                reverse=True,
            )
            return sorted_intents[0]

    def determine_clarification_strategy(
        self,
        intent: DetectedIntent,
        missing_slots: list[str],
    ) -> ClarificationStrategy:
        """Determine optimal clarification prompt strategy based on intent and missing required slots."""
        with self._lock:
            self._strategies_evaluated_count += 1
            if intent.confidence < 0.4:
                return ClarificationStrategy(
                    clarification_type=ClarificationType.AMBIGUOUS_INTENT,
                    prompt_text="I didn't quite catch that. Would you like to book a Puja, check Kundali, or search Muhurat?",
                    options=["Book Puja", "Check Kundali", "Search Muhurat"],
                )
            elif missing_slots:
                first_missing = missing_slots[0]
                readable_slot = first_missing.replace("_", " ").title()
                return ClarificationStrategy(
                    clarification_type=ClarificationType.MISSING_SLOT,
                    target_slot=first_missing,
                    prompt_text=f"Could you please provide the {readable_slot} for your {intent.intent_name.replace('_', ' ').title()}?",
                    options=[],
                )
            else:
                return ClarificationStrategy(
                    clarification_type=ClarificationType.CONFIRMATION_REQUIRED,
                    prompt_text="Please confirm your request.",
                )

    def determine_confirmation_strategy(
        self,
        intent: DetectedIntent,
        slots: dict[str, Any],
    ) -> ConfirmationStrategy:
        """Determine confirmation prompt strategy for intent and filled slots."""
        with self._lock:
            self._strategies_evaluated_count += 1
            slots_summary_text = ", ".join(f"{k.replace('_', ' ').title()}: {v}" for k, v in slots.items() if v)
            prompt = f"Please confirm: Do you want to proceed with {intent.intent_name.replace('_', ' ').title()} ({slots_summary_text})?"
            return ConfirmationStrategy(
                intent_name=intent.intent_name,
                confirmation_prompt=prompt,
                slots_summary=dict(slots),
                requires_explicit_yes=True,
            )

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose strategy engine operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "strategies_evaluated_count": self._strategies_evaluated_count,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            details=self.statistics(),
        )
