"""Domain models, value objects, and enums for Enterprise AI Conversation Framework v1.0."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, StrEnum
from typing import Any, Mapping
from uuid import uuid4


def _utc_now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 string format."""
    return datetime.now(timezone.utc).isoformat()


# ----------------------------------------------------------------------
# Centralized Enums
# ----------------------------------------------------------------------

class DialogueState(StrEnum):
    """Enumeration of conversation dialogue operational states."""

    IDLE = "IDLE"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    AWAITING_SLOT_INPUT = "AWAITING_SLOT_INPUT"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    AWAITING_CLARIFICATION = "AWAITING_CLARIFICATION"
    COMPLETED = "COMPLETED"
    INTERRUPTED = "INTERRUPTED"
    ESCALATED = "ESCALATED"
    ERROR = "ERROR"


class IntentCategory(StrEnum):
    """Enumeration of user intent domain categories."""

    BOOKING_PUJA = "BOOKING_PUJA"
    KUNDALI_INQUIRY = "KUNDALI_INQUIRY"
    MUHURAT_SEARCH = "MUHURAT_SEARCH"
    ASTROLOGER_CONSULT = "ASTROLOGER_CONSULT"
    GENERAL_INQUIRY = "GENERAL_INQUIRY"
    NAVIGATION_COMMAND = "NAVIGATION_COMMAND"
    SYSTEM_COMMAND = "SYSTEM_COMMAND"
    UNKNOWN = "UNKNOWN"


class ConfirmationStatus(StrEnum):
    """Enumeration of user confirmation states."""

    NONE = "NONE"
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class ClarificationType(StrEnum):
    """Enumeration of clarification prompt trigger types."""

    AMBIGUOUS_INTENT = "AMBIGUOUS_INTENT"
    MISSING_SLOT = "MISSING_SLOT"
    INVALID_VALUE = "INVALID_VALUE"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"


class PolicyViolationType(StrEnum):
    """Enumeration of conversational security and governance violations."""

    NONE = "NONE"
    UNAUTHENTICATED_ACCESS = "UNAUTHENTICATED_ACCESS"
    UNCONFIRMED_PAYMENT = "UNCONFIRMED_PAYMENT"
    SENSITIVE_DATA_EXPOSURE = "SENSITIVE_DATA_EXPOSURE"
    UNSUPPORTED_ACTION = "UNSUPPORTED_ACTION"


class RecoveryStrategyType(StrEnum):
    """Enumeration of dialogue failure recovery strategies."""

    REASK_SLOT = "REASK_SLOT"
    CLARIFY_INTENT = "CLARIFY_INTENT"
    RESTORE_CHECKPOINT = "RESTORE_CHECKPOINT"
    TRUNCATE_CONTEXT = "TRUNCATE_CONTEXT"
    FALLBACK_TO_HUMAN = "FALLBACK_TO_HUMAN"


# ----------------------------------------------------------------------
# Value Objects & Structs
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class ExtractedEntity:
    """Immutable named entity object extracted from user input."""

    entity_id: str = field(default_factory=lambda: str(uuid4()))
    entity_type: str = "UNKNOWN"
    raw_value: str = ""
    normalized_value: Any = None
    confidence: float = 1.0
    start_char: int = 0
    end_char: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "confidence": self.confidence,
            "start_char": self.start_char,
            "end_char": self.end_char,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExtractedEntity:
        return cls(
            entity_id=data.get("entity_id", str(uuid4())),
            entity_type=data.get("entity_type", "UNKNOWN"),
            raw_value=data.get("raw_value", ""),
            normalized_value=data.get("normalized_value"),
            confidence=float(data.get("confidence", 1.0)),
            start_char=int(data.get("start_char", 0)),
            end_char=int(data.get("end_char", 0)),
        )


@dataclass(frozen=True)
class DetectedIntent:
    """Immutable classified user intent object with confidence scoring."""

    intent_id: str = field(default_factory=lambda: str(uuid4()))
    intent_name: str = "UNKNOWN"
    category: IntentCategory = IntentCategory.UNKNOWN
    confidence: float = 0.0
    sub_intents: list[str] = field(default_factory=list)
    reasoning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "intent_name": self.intent_name,
            "category": str(self.category),
            "confidence": self.confidence,
            "sub_intents": list(self.sub_intents),
            "reasoning": self.reasoning,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DetectedIntent:
        return cls(
            intent_id=data.get("intent_id", str(uuid4())),
            intent_name=data.get("intent_name", "UNKNOWN"),
            category=IntentCategory(data.get("category", IntentCategory.UNKNOWN)),
            confidence=float(data.get("confidence", 0.0)),
            sub_intents=list(data.get("sub_intents") or []),
            reasoning=data.get("reasoning", ""),
        )


@dataclass(frozen=True)
class SlotRequirement:
    """Immutable definition of a slot required for intent fulfillment."""

    slot_name: str
    slot_type: str = "STRING"
    is_required: bool = True
    validation_rule: str = ""
    prompt_question: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_name": self.slot_name,
            "slot_type": self.slot_type,
            "is_required": self.is_required,
            "validation_rule": self.validation_rule,
            "prompt_question": self.prompt_question,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SlotRequirement:
        return cls(
            slot_name=data.get("slot_name", ""),
            slot_type=data.get("slot_type", "STRING"),
            is_required=bool(data.get("is_required", True)),
            validation_rule=data.get("validation_rule", ""),
            prompt_question=data.get("prompt_question", ""),
        )


@dataclass
class SlotValue:
    """Mutable representation of an extracted/confirmed slot value."""

    slot_name: str
    value: Any = None
    is_validated: bool = False
    confidence: float = 1.0
    updated_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_name": self.slot_name,
            "value": self.value,
            "is_validated": self.is_validated,
            "confidence": self.confidence,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SlotValue:
        return cls(
            slot_name=data.get("slot_name", ""),
            value=data.get("value"),
            is_validated=bool(data.get("is_validated", False)),
            confidence=float(data.get("confidence", 1.0)),
            updated_at=data.get("updated_at", _utc_now_iso()),
        )


@dataclass(frozen=True)
class DialogueCheckpoint:
    """Immutable snapshot of conversation state for recovery and resume."""

    checkpoint_id: str = field(default_factory=lambda: str(uuid4()))
    state_name: DialogueState = DialogueState.IDLE
    confirmed_slots: dict[str, Any] = field(default_factory=dict)
    active_intent: str | None = None
    saved_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "state_name": str(self.state_name),
            "confirmed_slots": dict(self.confirmed_slots),
            "active_intent": self.active_intent,
            "saved_at": self.saved_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DialogueCheckpoint:
        return cls(
            checkpoint_id=data.get("checkpoint_id", str(uuid4())),
            state_name=DialogueState(data.get("state_name", DialogueState.IDLE)),
            confirmed_slots=dict(data.get("confirmed_slots") or {}),
            active_intent=data.get("active_intent"),
            saved_at=data.get("saved_at", _utc_now_iso()),
        )


@dataclass
class DialogueTurn:
    """Representation of an individual conversation turn."""

    turn_id: str = field(default_factory=lambda: str(uuid4()))
    turn_index: int = 0
    speaker: str = "USER"  # "USER" or "ASSISTANT"
    utterance: str = ""
    detected_intent: DetectedIntent | None = None
    entities: list[ExtractedEntity] = field(default_factory=list)
    slots: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "turn_index": self.turn_index,
            "speaker": self.speaker,
            "utterance": self.utterance,
            "detected_intent": self.detected_intent.to_dict() if self.detected_intent else None,
            "entities": [e.to_dict() for e in self.entities],
            "slots": dict(self.slots),
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DialogueTurn:
        intent_dict = data.get("detected_intent")
        intent = DetectedIntent.from_dict(intent_dict) if intent_dict else None
        entities = [ExtractedEntity.from_dict(ed) for ed in data.get("entities", [])]
        return cls(
            turn_id=data.get("turn_id", str(uuid4())),
            turn_index=int(data.get("turn_index", 0)),
            speaker=data.get("speaker", "USER"),
            utterance=data.get("utterance", ""),
            detected_intent=intent,
            entities=entities,
            slots=dict(data.get("slots") or {}),
            timestamp=data.get("timestamp", _utc_now_iso()),
        )


@dataclass(frozen=True)
class PolicyEvaluationResult:
    """Result object from ConversationPolicyEngine policy evaluation."""

    is_allowed: bool
    violation_type: PolicyViolationType = PolicyViolationType.NONE
    reason: str = ""
    required_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_allowed": self.is_allowed,
            "violation_type": str(self.violation_type),
            "reason": self.reason,
            "required_action": self.required_action,
        }


@dataclass(frozen=True)
class ClarificationStrategy:
    """Strategy object for clarifying ambiguous intents or missing slots."""

    clarification_type: ClarificationType
    target_slot: str | None = None
    prompt_text: str = ""
    options: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "clarification_type": str(self.clarification_type),
            "target_slot": self.target_slot,
            "prompt_text": self.prompt_text,
            "options": list(self.options),
        }


@dataclass(frozen=True)
class ConfirmationStrategy:
    """Strategy object for seeking user confirmation on sensitive/completed actions."""

    intent_name: str
    confirmation_prompt: str
    slots_summary: dict[str, Any] = field(default_factory=dict)
    requires_explicit_yes: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_name": self.intent_name,
            "confirmation_prompt": self.confirmation_prompt,
            "slots_summary": dict(self.slots_summary),
            "requires_explicit_yes": self.requires_explicit_yes,
        }


@dataclass(frozen=True)
class RecoveryResult:
    """Result object from ConversationRecoveryEngine strategy execution."""

    success: bool
    recovery_strategy: RecoveryStrategyType
    new_state: DialogueState
    message: str = ""
    restored_checkpoint: DialogueCheckpoint | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "recovery_strategy": str(self.recovery_strategy),
            "new_state": str(self.new_state),
            "message": self.message,
            "restored_checkpoint": self.restored_checkpoint.to_dict() if self.restored_checkpoint else None,
        }


@dataclass
class ConversationSnapshot:
    """Complete serializable snapshot of a session conversation state."""

    snapshot_id: str = field(default_factory=lambda: str(uuid4()))
    session_id: str = ""
    dialogue_state: DialogueState = DialogueState.IDLE
    active_intent: DetectedIntent | None = None
    confirmed_slots: dict[str, Any] = field(default_factory=dict)
    pending_slots: list[str] = field(default_factory=list)
    turns: list[DialogueTurn] = field(default_factory=list)
    checkpoint: DialogueCheckpoint | None = None
    created_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "session_id": self.session_id,
            "dialogue_state": str(self.dialogue_state),
            "active_intent": self.active_intent.to_dict() if self.active_intent else None,
            "confirmed_slots": dict(self.confirmed_slots),
            "pending_slots": list(self.pending_slots),
            "turns": [t.to_dict() for t in self.turns],
            "checkpoint": self.checkpoint.to_dict() if self.checkpoint else None,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConversationSnapshot:
        intent_dict = data.get("active_intent")
        intent = DetectedIntent.from_dict(intent_dict) if intent_dict else None
        turns = [DialogueTurn.from_dict(td) for td in data.get("turns", [])]
        ckpt_dict = data.get("checkpoint")
        ckpt = DialogueCheckpoint.from_dict(ckpt_dict) if ckpt_dict else None
        return cls(
            snapshot_id=data.get("snapshot_id", str(uuid4())),
            session_id=data.get("session_id", ""),
            dialogue_state=DialogueState(data.get("dialogue_state", DialogueState.IDLE)),
            active_intent=intent,
            confirmed_slots=dict(data.get("confirmed_slots") or {}),
            pending_slots=list(data.get("pending_slots") or []),
            turns=turns,
            checkpoint=ckpt,
            created_at=data.get("created_at", _utc_now_iso()),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> ConversationSnapshot:
        return cls.from_dict(json.loads(json_str))
