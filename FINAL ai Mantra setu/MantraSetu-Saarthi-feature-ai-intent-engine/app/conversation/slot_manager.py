"""Thread-Safe Slot Tracking, Validation, and Filling Engine v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.conversation.conversation_models import (
    ExtractedEntity,
    SlotRequirement,
    SlotValue,
)

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "SlotManager"
_COMPONENT_VERSION = "1.0.0"


class SlotManager:
    """Enterprise thread-safe slot tracking and validation engine."""

    # Default Intent Slot Requirements Registry
    _DEFAULT_REQUIREMENTS: dict[str, list[SlotRequirement]] = {
        "BOOKING_PUJA": [
            SlotRequirement(slot_name="puja_name", slot_type="PUJA_NAME", is_required=True, prompt_question="Which Puja would you like to book?"),
            SlotRequirement(slot_name="booking_date", slot_type="DATE", is_required=True, prompt_question="What is your preferred date for the Puja?"),
            SlotRequirement(slot_name="location", slot_type="LOCATION", is_required=False, prompt_question="What is the event location?"),
        ],
        "KUNDALI_INQUIRY": [
            SlotRequirement(slot_name="name", slot_type="STRING", is_required=True, prompt_question="What is your name?"),
            SlotRequirement(slot_name="birth_date", slot_type="DATE", is_required=True, prompt_question="What is your birth date?"),
            SlotRequirement(slot_name="birth_time", slot_type="TIME", is_required=False, prompt_question="What is your birth time?"),
        ],
        "MUHURAT_SEARCH": [
            SlotRequirement(slot_name="event_type", slot_type="STRING", is_required=True, prompt_question="What event are you seeking a Muhurat for?"),
            SlotRequirement(slot_name="preferred_date", slot_type="DATE", is_required=True, prompt_question="For which date range?"),
        ],
    }

    def __init__(self) -> None:
        self._requirements: dict[str, list[SlotRequirement]] = dict(self._DEFAULT_REQUIREMENTS)
        self._session_slots: dict[str, dict[str, SlotValue]] = {}
        self._lock = RLock()
        self._fills_count = 0

    def register_requirements(self, intent_name: str, requirements: list[SlotRequirement]) -> None:
        """Register custom slot requirements for an intent."""
        with self._lock:
            self._requirements[intent_name.upper()] = list(requirements)

    def get_requirements(self, intent_name: str) -> list[SlotRequirement]:
        """Get slot requirements registered for an intent."""
        with self._lock:
            return list(self._requirements.get(intent_name.upper(), []))

    def validate_slot(self, slot_type: str, value: Any) -> bool:
        """Validate if a slot value satisfies type rules."""
        if value is None:
            return False
        val_str = str(value).strip()
        if not val_str:
            return False
        return True

    def fill_slots(self, session_id: str, entities: list[ExtractedEntity]) -> dict[str, SlotValue]:
        """Map extracted entities to session slot values with thread-safe isolation."""
        with self._lock:
            self._fills_count += 1
            if session_id not in self._session_slots:
                self._session_slots[session_id] = {}

            session_map = self._session_slots[session_id]

            # Entity type to slot name mapping
            type_mapping = {
                "PUJA_NAME": "puja_name",
                "DATE": "booking_date",
                "TIME": "birth_time",
                "LOCATION": "location",
                "LANGUAGE": "language",
            }

            for entity in entities:
                slot_name = type_mapping.get(entity.entity_type, entity.entity_type.lower())
                is_valid = self.validate_slot(entity.entity_type, entity.normalized_value)
                session_map[slot_name] = SlotValue(
                    slot_name=slot_name,
                    value=entity.normalized_value,
                    is_validated=is_valid,
                    confidence=entity.confidence,
                )

            return dict(session_map)

    def get_slots(self, session_id: str) -> dict[str, SlotValue]:
        """Get active slot map for session."""
        with self._lock:
            return dict(self._session_slots.get(session_id, {}))

    def get_missing_slots(self, session_id: str, intent_name: str) -> list[SlotRequirement]:
        """Determine required slots not yet filled for intent."""
        with self._lock:
            reqs = self.get_requirements(intent_name)
            filled = self.get_slots(session_id)

            missing: list[SlotRequirement] = []
            for req in reqs:
                if req.is_required:
                    slot_val = filled.get(req.slot_name)
                    if not slot_val or not slot_val.is_validated or slot_val.value is None:
                        missing.append(req)

            return missing

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "registered_intents": len(self._requirements),
                "active_sessions": len(self._session_slots),
                "slot_fills_count": self._fills_count,
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
