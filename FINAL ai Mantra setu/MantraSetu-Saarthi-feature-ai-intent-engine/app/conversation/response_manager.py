"""Clarification, Confirmation & Response Formatting Manager v1.0."""

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
    DialogueState,
)

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ResponseManager"
_COMPONENT_VERSION = "1.0.0"


class ResponseManager:
    """Enterprise response manager generating deterministic clarification, confirmation, and assistant payload outputs."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._responses_generated_count = 0

    def generate_clarification(
        self,
        clarification_type: ClarificationType,
        missing_slots: list[str] | None = None,
    ) -> ClarificationStrategy:
        """Generate clarification strategy for ambiguous inputs or missing slots."""
        with self._lock:
            self._responses_generated_count += 1
            missing_slots = missing_slots or []

            if clarification_type == ClarificationType.MISSING_SLOT and missing_slots:
                first_missing = missing_slots[0]
                label = first_missing.replace("_", " ").title()
                return ClarificationStrategy(
                    clarification_type=ClarificationType.MISSING_SLOT,
                    target_slot=first_missing,
                    prompt_text=f"Please provide the {label} to proceed.",
                )
            elif clarification_type == ClarificationType.AMBIGUOUS_INTENT:
                return ClarificationStrategy(
                    clarification_type=ClarificationType.AMBIGUOUS_INTENT,
                    prompt_text="Could you please clarify your request? You can book a Puja, check Kundali, or search Muhurat.",
                    options=["Book Puja", "Check Kundali", "Search Muhurat"],
                )
            else:
                return ClarificationStrategy(
                    clarification_type=ClarificationType.CONFIRMATION_REQUIRED,
                    prompt_text="Please confirm your selection.",
                )

    def generate_confirmation_prompt(
        self,
        intent: DetectedIntent,
        slots: dict[str, Any],
    ) -> ConfirmationStrategy:
        """Generate confirmation strategy prompt for user verification."""
        with self._lock:
            self._responses_generated_count += 1
            slots_summary_text = ", ".join(f"{k.replace('_', ' ').title()}: {v}" for k, v in slots.items() if v)
            prompt = f"Please confirm: Do you want to proceed with {intent.intent_name.replace('_', ' ').title()} ({slots_summary_text})?"
            return ConfirmationStrategy(
                intent_name=intent.intent_name,
                confirmation_prompt=prompt,
                slots_summary=dict(slots),
                requires_explicit_yes=True,
            )

    def format_assistant_response(
        self,
        utterance: str,
        dialogue_state: DialogueState,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Format standardized assistant response dictionary."""
        with self._lock:
            self._responses_generated_count += 1
            return {
                "utterance": utterance,
                "dialogue_state": str(dialogue_state),
                "payload": dict(payload or {}),
            }

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "responses_generated_count": self._responses_generated_count,
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
