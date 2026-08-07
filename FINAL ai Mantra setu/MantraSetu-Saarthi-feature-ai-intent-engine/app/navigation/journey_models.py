"""Domain models, enums, and schemas for Enterprise Navigation Journey Intelligence v4.1."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum, StrEnum
from typing import Any, Mapping
from uuid import UUID, uuid4


def _utc_now_iso() -> str:
    """Return current timestamp in ISO 8601 format with UTC timezone."""
    return datetime.now(timezone.utc).isoformat()


# ----------------------------------------------------------------------
# Centralized String Enums
# ----------------------------------------------------------------------

class TransitionStatus(StrEnum):
    """Enumeration of screen transition execution statuses."""

    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    CANCELLED = "CANCELLED"
    INTERRUPTED = "INTERRUPTED"
    ROLLED_BACK = "ROLLED_BACK"
    RESUMED = "RESUMED"
    FAILED = "FAILED"


class FrontendEventType(StrEnum):
    """Enumeration of standard frontend navigation lifecycle event types."""

    PAGE_CHANGED = "PAGE_CHANGED"
    NAVIGATION_STARTED = "NAVIGATION_STARTED"
    NAVIGATION_COMPLETED = "NAVIGATION_COMPLETED"
    BROWSER_BACK = "BROWSER_BACK"
    BROWSER_FORWARD = "BROWSER_FORWARD"
    REFRESH = "REFRESH"
    MODAL_OPENED = "MODAL_OPENED"
    MODAL_CLOSED = "MODAL_CLOSED"
    TAB_CHANGED = "TAB_CHANGED"
    SECTION_CHANGED = "SECTION_CHANGED"
    FORM_SUBMITTED = "FORM_SUBMITTED"
    BUTTON_CLICKED = "BUTTON_CLICKED"
    LINK_CLICKED = "LINK_CLICKED"
    CARD_SELECTED = "CARD_SELECTED"
    DROPDOWN_CHANGED = "DROPDOWN_CHANGED"
    PAYMENT_SUCCESS = "PAYMENT_SUCCESS"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    OTP_VERIFIED = "OTP_VERIFIED"
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGOUT = "LOGOUT"


class NavigationEventPriority(StrEnum):
    """Enumeration of event processing priorities."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ReplayMode(StrEnum):
    """Enumeration of session replay execution modes."""

    FULL_REPLAY = "FULL_REPLAY"
    WORKFLOW_ONLY = "WORKFLOW_ONLY"
    FAILED_TRANSITIONS_ONLY = "FAILED_TRANSITIONS_ONLY"
    USER_ACTIONS_ONLY = "USER_ACTIONS_ONLY"
    AI_DECISIONS_ONLY = "AI_DECISIONS_ONLY"


class AcknowledgementState(StrEnum):
    """Enumeration of frontend event acknowledgement states."""

    RECEIVED = "RECEIVED"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"
    IGNORED = "IGNORED"


# ----------------------------------------------------------------------
# Value Objects & Structs
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class PredictedRoute:
    """Structured navigation destination prediction object with confidence metrics."""

    route: str
    confidence: float  # Range: 0.0 to 1.0
    reason: str = ""
    confidence_source: str = "METADATA_GRAPH"
    prediction_timestamp: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "route": self.route,
            "confidence": self.confidence,
            "reason": self.reason,
            "confidence_source": self.confidence_source,
            "prediction_timestamp": self.prediction_timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PredictedRoute:
        return cls(
            route=data.get("route", "/"),
            confidence=float(data.get("confidence", 0.0)),
            reason=data.get("reason", ""),
            confidence_source=data.get("confidence_source", "METADATA_GRAPH"),
            prediction_timestamp=data.get("prediction_timestamp", _utc_now_iso()),
        )


@dataclass(frozen=True)
class UITransitionChain:
    """Fine-grained UI element transition chain metadata."""

    section_id: str | None = None
    card_id: str | None = None
    component_id: str | None = None
    component_type: str | None = None
    action_name: str | None = None
    ui_context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_id": self.section_id,
            "card_id": self.card_id,
            "component_id": self.component_id,
            "component_type": self.component_type,
            "action_name": self.action_name,
            "ui_context": dict(self.ui_context),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> UITransitionChain | None:
        if not data:
            return None
        return cls(
            section_id=data.get("section_id"),
            card_id=data.get("card_id"),
            component_id=data.get("component_id"),
            component_type=data.get("component_type"),
            action_name=data.get("action_name"),
            ui_context=dict(data.get("ui_context") or {}),
        )


@dataclass(frozen=True)
class EventAcknowledgement:
    """Non-blocking frontend event acknowledgement response object."""

    event_id: str
    event_type: str
    session_id: str
    status: AcknowledgementState
    timestamp: str = field(default_factory=_utc_now_iso)
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "session_id": self.session_id,
            "status": str(self.status),
            "timestamp": self.timestamp,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EventAcknowledgement:
        return cls(
            event_id=data.get("event_id", str(uuid4())),
            event_type=data.get("event_type", "UNKNOWN"),
            session_id=data.get("session_id", ""),
            status=AcknowledgementState(data.get("status", AcknowledgementState.PROCESSED)),
            timestamp=data.get("timestamp", _utc_now_iso()),
            error_message=data.get("error_message"),
        )


@dataclass
class NavigationTransition:
    """Core domain model representing a single screen-to-screen transition event."""

    transition_id: str = field(default_factory=lambda: str(uuid4()))
    session_id: str = ""
    conversation_id: str = ""
    workflow_id: str | None = None
    workflow_step: str | None = None
    previous_page: str = "/"
    current_page: str = "/"
    target_page: str = "/"
    navigation_action: str = "NAVIGATE"
    triggering_ui_element: str | None = None
    triggering_ai_intent: str | None = None
    ui_transition_chain: UITransitionChain | None = None
    timestamp: str = field(default_factory=_utc_now_iso)
    priority: NavigationEventPriority = NavigationEventPriority.MEDIUM
    transition_status: TransitionStatus = TransitionStatus.SUCCESS
    transition_duration: float = 0.0  # Milliseconds
    recovery_point: dict[str, Any] | None = None
    interruption_reason: str | None = None
    # Distributed tracing identifiers
    trace_id: str | None = None
    request_id: str | None = None
    decision_id: str | None = None
    plan_id: str | None = None
    execution_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize entity to defensive plain dictionary."""
        return {
            "transition_id": self.transition_id,
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "workflow_id": self.workflow_id,
            "workflow_step": self.workflow_step,
            "previous_page": self.previous_page,
            "current_page": self.current_page,
            "target_page": self.target_page,
            "navigation_action": self.navigation_action,
            "triggering_ui_element": self.triggering_ui_element,
            "triggering_ai_intent": self.triggering_ai_intent,
            "ui_transition_chain": self.ui_transition_chain.to_dict() if self.ui_transition_chain else None,
            "timestamp": self.timestamp,
            "priority": str(self.priority),
            "transition_status": str(self.transition_status),
            "transition_duration": self.transition_duration,
            "recovery_point": dict(self.recovery_point) if self.recovery_point else None,
            "interruption_reason": self.interruption_reason,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "decision_id": self.decision_id,
            "plan_id": self.plan_id,
            "execution_id": self.execution_id,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NavigationTransition:
        """Deserialize entity from dictionary representation."""
        ui_chain_dict = data.get("ui_transition_chain")
        ui_chain = UITransitionChain.from_dict(ui_chain_dict) if ui_chain_dict else None
        return cls(
            transition_id=data.get("transition_id", str(uuid4())),
            session_id=data.get("session_id", ""),
            conversation_id=data.get("conversation_id", ""),
            workflow_id=data.get("workflow_id"),
            workflow_step=data.get("workflow_step"),
            previous_page=data.get("previous_page", "/"),
            current_page=data.get("current_page", "/"),
            target_page=data.get("target_page", "/"),
            navigation_action=data.get("navigation_action", "NAVIGATE"),
            triggering_ui_element=data.get("triggering_ui_element"),
            triggering_ai_intent=data.get("triggering_ai_intent"),
            ui_transition_chain=ui_chain,
            timestamp=data.get("timestamp", _utc_now_iso()),
            priority=NavigationEventPriority(data.get("priority", NavigationEventPriority.MEDIUM)),
            transition_status=TransitionStatus(data.get("transition_status", TransitionStatus.SUCCESS)),
            transition_duration=float(data.get("transition_duration", 0.0)),
            recovery_point=dict(data.get("recovery_point")) if data.get("recovery_point") else None,
            interruption_reason=data.get("interruption_reason"),
            trace_id=data.get("trace_id"),
            request_id=data.get("request_id"),
            decision_id=data.get("decision_id"),
            plan_id=data.get("plan_id"),
            execution_id=data.get("execution_id"),
            metadata=dict(data.get("metadata") or {}),
        )

    def to_json(self) -> str:
        """Serialize entity to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> NavigationTransition:
        """Deserialize entity from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class JourneyCheckpoint:
    """Resume checkpoint model for interrupted user workflows."""

    checkpoint_id: str = field(default_factory=lambda: str(uuid4()))
    workflow_id: str = ""
    workflow_name: str = ""
    step_name: str = ""
    step_index: int = 0
    route_page: str = "/"
    route_parameters: dict[str, Any] = field(default_factory=dict)
    form_data: dict[str, Any] = field(default_factory=dict)
    saved_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "step_name": self.step_name,
            "step_index": self.step_index,
            "route_page": self.route_page,
            "route_parameters": dict(self.route_parameters),
            "form_data": dict(self.form_data),
            "saved_at": self.saved_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JourneyCheckpoint:
        return cls(
            checkpoint_id=data.get("checkpoint_id", str(uuid4())),
            workflow_id=data.get("workflow_id", ""),
            workflow_name=data.get("workflow_name", ""),
            step_name=data.get("step_name", ""),
            step_index=int(data.get("step_index", 0)),
            route_page=data.get("route_page", "/"),
            route_parameters=dict(data.get("route_parameters") or {}),
            form_data=dict(data.get("form_data") or {}),
            saved_at=data.get("saved_at", _utc_now_iso()),
        )


@dataclass
class UserBehaviourProfile:
    """User navigation profile containing behavioral aggregates."""

    most_visited_pages: list[tuple[str, int]] = field(default_factory=list)
    most_visited_workflows: list[tuple[str, int]] = field(default_factory=list)
    most_used_components: list[tuple[str, int]] = field(default_factory=list)
    average_session_length_seconds: float = 0.0
    average_booking_completion_time_seconds: float = 0.0
    workflow_completion_rate: float = 0.0
    interruption_rate: float = 0.0
    average_resume_time_seconds: float = 0.0
    average_navigation_depth: float = 0.0
    average_steps_per_session: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "most_visited_pages": [list(item) for item in self.most_visited_pages],
            "most_visited_workflows": [list(item) for item in self.most_visited_workflows],
            "most_used_components": [list(item) for item in self.most_used_components],
            "average_session_length_seconds": self.average_session_length_seconds,
            "average_booking_completion_time_seconds": self.average_booking_completion_time_seconds,
            "workflow_completion_rate": self.workflow_completion_rate,
            "interruption_rate": self.interruption_rate,
            "average_resume_time_seconds": self.average_resume_time_seconds,
            "average_navigation_depth": self.average_navigation_depth,
            "average_steps_per_session": self.average_steps_per_session,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserBehaviourProfile:
        return cls(
            most_visited_pages=[(t[0], t[1]) for t in data.get("most_visited_pages", [])],
            most_visited_workflows=[(t[0], t[1]) for t in data.get("most_visited_workflows", [])],
            most_used_components=[(t[0], t[1]) for t in data.get("most_used_components", [])],
            average_session_length_seconds=float(data.get("average_session_length_seconds", 0.0)),
            average_booking_completion_time_seconds=float(data.get("average_booking_completion_time_seconds", 0.0)),
            workflow_completion_rate=float(data.get("workflow_completion_rate", 0.0)),
            interruption_rate=float(data.get("interruption_rate", 0.0)),
            average_resume_time_seconds=float(data.get("average_resume_time_seconds", 0.0)),
            average_navigation_depth=float(data.get("average_navigation_depth", 0.0)),
            average_steps_per_session=float(data.get("average_steps_per_session", 0.0)),
        )


@dataclass
class NavigationJourney:
    """Core domain model representing the complete session navigation timeline."""

    journey_id: str = field(default_factory=lambda: str(uuid4()))
    session_id: str = ""
    conversation_id: str = ""
    transitions: list[NavigationTransition] = field(default_factory=list)
    active_workflow: str | None = None
    workflow_step: str | None = None
    resume_checkpoint: JourneyCheckpoint | None = None
    started_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)
    is_archived: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize journey to defensive plain dictionary."""
        return {
            "journey_id": self.journey_id,
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "transitions": [t.to_dict() for t in self.transitions],
            "active_workflow": self.active_workflow,
            "workflow_step": self.workflow_step,
            "resume_checkpoint": self.resume_checkpoint.to_dict() if self.resume_checkpoint else None,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "is_archived": self.is_archived,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NavigationJourney:
        """Deserialize journey from dictionary representation."""
        t_list = [NavigationTransition.from_dict(td) for td in data.get("transitions", [])]
        ckpt_dict = data.get("resume_checkpoint")
        ckpt = JourneyCheckpoint.from_dict(ckpt_dict) if ckpt_dict else None
        return cls(
            journey_id=data.get("journey_id", str(uuid4())),
            session_id=data.get("session_id", ""),
            conversation_id=data.get("conversation_id", ""),
            transitions=t_list,
            active_workflow=data.get("active_workflow"),
            workflow_step=data.get("workflow_step"),
            resume_checkpoint=ckpt,
            started_at=data.get("started_at", _utc_now_iso()),
            updated_at=data.get("updated_at", _utc_now_iso()),
            is_archived=bool(data.get("is_archived", False)),
        )

    def to_json(self) -> str:
        """Serialize journey entity to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> NavigationJourney:
        """Deserialize journey entity from JSON string."""
        return cls.from_dict(json.loads(json_str))
