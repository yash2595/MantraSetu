"""Domain models, value objects, and enums for Enterprise Voice Form Automation Framework v1.0."""

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

class FormState(StrEnum):
    """Enumeration of form workflow session states."""

    IDLE = "IDLE"
    DISCOVERED = "DISCOVERED"
    FILLING = "FILLING"
    AWAITING_INPUT = "AWAITING_INPUT"
    VALIDATED = "VALIDATED"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    SUBMITTED = "SUBMITTED"
    FAILED = "FAILED"


class FieldState(StrEnum):
    """Enumeration of individual form field states."""

    UNTOUCHED = "UNTOUCHED"
    FOCUSED = "FOCUSED"
    FILLED = "FILLED"
    VALIDATED = "VALIDATED"
    ERROR = "ERROR"
    CORRECTED = "CORRECTED"


class ValidationState(StrEnum):
    """Enumeration of field/form validation outcomes."""

    UNVALIDATED = "UNVALIDATED"
    PASSED = "PASSED"
    FAILED = "FAILED"
    PENDING = "PENDING"


class SubmissionState(StrEnum):
    """Enumeration of form submission lifecycle states."""

    DRAFT = "DRAFT"
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    SUBMITTING = "SUBMITTING"
    SUBMITTED = "SUBMITTED"
    REJECTED = "REJECTED"


class FieldType(StrEnum):
    """Enumeration of supported HTML/React input field types."""

    TEXT = "TEXT"
    NUMBER = "NUMBER"
    DATE = "DATE"
    TIME = "TIME"
    SELECT = "SELECT"
    RADIO = "RADIO"
    CHECKBOX = "CHECKBOX"
    FILE = "FILE"
    OTP = "OTP"
    PAYMENT_CARD = "PAYMENT_CARD"


# ----------------------------------------------------------------------
# Value Objects & Structs
# ----------------------------------------------------------------------

@dataclass
class FormField:
    """Model defining an individual form input field schema."""

    field_id: str = field(default_factory=lambda: str(uuid4()))
    field_name: str = ""
    field_label: str = ""
    field_type: FieldType = FieldType.TEXT
    is_required: bool = True
    validation_regex: str | None = None
    aliases: list[str] = field(default_factory=list)
    state: FieldState = FieldState.UNTOUCHED

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_id": self.field_id,
            "field_name": self.field_name,
            "field_label": self.field_label,
            "field_type": str(self.field_type),
            "is_required": self.is_required,
            "validation_regex": self.validation_regex,
            "aliases": list(self.aliases),
            "state": str(self.state),
        }


@dataclass
class FieldValue:
    """Model representing a populated field value."""

    field_name: str = ""
    value: Any = None
    confidence: float = 1.0
    is_user_confirmed: bool = False
    updated_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_name": self.field_name,
            "value": self.value,
            "confidence": self.confidence,
            "is_user_confirmed": self.is_user_confirmed,
            "updated_at": self.updated_at,
        }


@dataclass
class FormDefinition:
    """Enterprise model defining a full web form UI structure."""

    form_id: str = field(default_factory=lambda: str(uuid4()))
    form_name: str = ""
    target_route: str = "/"
    fields: list[FormField] = field(default_factory=list)
    supported_intents: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "form_id": self.form_id,
            "form_name": self.form_name,
            "target_route": self.target_route,
            "fields": [f.to_dict() for f in self.fields],
            "supported_intents": list(self.supported_intents),
        }


@dataclass
class FormSession:
    """Model representing an active voice form filling session."""

    session_id: str = field(default_factory=lambda: str(uuid4()))
    form_id: str = ""
    state: FormState = FormState.IDLE
    filled_values: dict[str, FieldValue] = field(default_factory=dict)
    current_field_focus: str | None = None
    started_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "form_id": self.form_id,
            "state": str(self.state),
            "filled_values": {k: v.to_dict() for k, v in self.filled_values.items()},
            "current_field_focus": self.current_field_focus,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class FieldValidation:
    """Validation report object for an individual field."""

    field_name: str
    state: ValidationState
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_name": self.field_name,
            "state": str(self.state),
            "error_message": self.error_message,
        }


@dataclass(frozen=True)
class FormProgress:
    """Progress snapshot object for form completion."""

    form_id: str
    total_fields: int
    completed_fields: int
    completion_percentage: float
    missing_required_fields: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "form_id": self.form_id,
            "total_fields": self.total_fields,
            "completed_fields": self.completed_fields,
            "completion_percentage": self.completion_percentage,
            "missing_required_fields": list(self.missing_required_fields),
        }


@dataclass(frozen=True)
class FormSnapshot:
    """Immutable snapshot model for draft saving and recovery."""

    snapshot_id: str = field(default_factory=lambda: str(uuid4()))
    session_id: str = ""
    form_id: str = ""
    values: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "session_id": self.session_id,
            "form_id": self.form_id,
            "values": dict(self.values),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class FormDirective:
    """WebSocket UI directive frame sent to Frontend Bridge."""

    directive_id: str = field(default_factory=lambda: str(uuid4()))
    action: str = "POPULATE_FIELD"  # POPULATE_FIELD | HIGHLIGHT_FIELD | CLEAR_FIELD | SHOW_CONFIRMATION_MODAL
    field_name: str = ""
    value: Any = None
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "directive_id": self.directive_id,
            "action": self.action,
            "field_name": self.field_name,
            "value": self.value,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class FormDiagnostics:
    """Operational diagnostics object for form automation framework."""

    session_id: str
    active_form_id: str
    completion_percentage: float
    validation_errors_count: int
    corrections_count: int
