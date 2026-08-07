"""Real-time Frontend-AI Event Synchronization Manager for MantraSetu AgentOS v4.1."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any
from uuid import uuid4

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.journey_models import (
    AcknowledgementState,
    EventAcknowledgement,
    FrontendEventType,
    JourneyCheckpoint,
    NavigationEventPriority,
    NavigationTransition,
    TransitionStatus,
    UITransitionChain,
)
from app.navigation.journey_store import NavigationJourneyStore
from app.navigation.state_store import NavigationStateStore
from app.navigation.workflow_tracker import WorkflowTracker

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "NavigationSyncManager"
_COMPONENT_VERSION = "4.1"


class NavigationSyncManager:
    """Manager handling real-time frontend lifecycle sync events, priority processing, and state store alignment."""

    def __init__(
        self,
        state_store: NavigationStateStore | None = None,
        workflow_tracker: WorkflowTracker | None = None,
        journey_store: NavigationJourneyStore | None = None,
    ) -> None:
        self._state_store = state_store or NavigationStateStore()
        self._workflow_tracker = workflow_tracker or WorkflowTracker(self._state_store)
        self._journey_store = journey_store or NavigationJourneyStore()
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._events_processed_count = 0

    def _resolve_event_priority(self, event_type: str) -> NavigationEventPriority:
        """Map raw frontend event string to event priority level."""
        evt = event_type.upper()
        if evt in ("PAYMENT_SUCCESS", "PAYMENT_FAILED", "LOGIN_SUCCESS", "LOGIN", "LOGOUT", "OTP_VERIFIED"):
            return NavigationEventPriority.HIGH
        elif evt in ("PAGE_CHANGED", "PAGE_LOADED", "NAVIGATION_COMPLETED", "FORM_SUBMITTED", "BUTTON_CLICKED"):
            return NavigationEventPriority.MEDIUM
        else:
            return NavigationEventPriority.LOW

    def handle_frontend_event(
        self,
        session_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Handle incoming frontend lifecycle sync event and update navigation state store."""
        with self._lock:
            start_ts = time.perf_counter()
            self._events_processed_count += 1
            payload = payload or {}
            event_name = event_type.upper()
            priority = self._resolve_event_priority(event_name)
            logger.debug("Processing frontend sync event '%s' [Priority: %s] for session '%s'", event_name, priority, session_id)

            session_state = self._state_store.get_state(session_id)
            prev_page = session_state.current_page or "/"

            # Extract UI transition chain if provided
            ui_chain = None
            if any(k in payload for k in ("section_id", "card_id", "component_id", "component_type", "action_name")):
                ui_chain = UITransitionChain(
                    section_id=payload.get("section_id"),
                    card_id=payload.get("card_id"),
                    component_id=payload.get("component_id"),
                    component_type=payload.get("component_type"),
                    action_name=payload.get("action_name"),
                    ui_context=payload.get("ui_context") or {},
                )

            # Processing logic
            res_dict: dict[str, Any] = {"status": "SUCCESS", "event": event_name}
            curr_page = prev_page

            if event_name in ("PAGE_CHANGED", "PAGE_LOADED", "NAVIGATION_COMPLETED", "PAGE_REFRESH", "SESSION_RESTORED"):
                curr_page = payload.get("path", payload.get("url", "/"))
                params = payload.get("parameters", {})
                state = self._state_store.update_current_page(session_id, curr_page, params)
                res_dict["state"] = state.to_dict()

            elif event_name == "BROWSER_BACK":
                restored = self._state_store.undo(session_id)
                state = self._state_store.get_state(session_id)
                curr_page = restored or state.current_page
                res_dict["restored_page"] = restored
                res_dict["state"] = state.to_dict()

            elif event_name == "BROWSER_FORWARD":
                state = self._state_store.get_state(session_id)
                curr_page = state.current_page
                res_dict["state"] = state.to_dict()

            elif event_name == "WORKFLOW_STARTED":
                wf_name = payload.get("workflow_name", "UNKNOWN_WORKFLOW")
                init_step = payload.get("initial_step", "INIT")
                wf_ctx = self._workflow_tracker.start_workflow(session_id, wf_name, init_step)
                res_dict["workflow"] = wf_ctx.to_dict()

            elif event_name == "WORKFLOW_CANCELLED":
                self._workflow_tracker.cancel_workflow(session_id)

            elif event_name in ("FORM_UPDATED", "INPUT_CHANGED", "FORM_SUBMITTED"):
                field_name = payload.get("field")
                val = payload.get("value")
                if field_name:
                    session_state.current_route_parameters[field_name] = val
                res_dict["state"] = session_state.to_dict()

            elif event_name in ("LOGIN", "LOGIN_SUCCESS", "PAYMENT_SUCCESS"):
                session_state.auth_state = "AUTHENTICATED"
                res_dict["state"] = session_state.to_dict()

            elif event_name in ("LOGOUT", "PAYMENT_FAILED"):
                session_state.auth_state = "ANONYMOUS"
                res_dict["state"] = session_state.to_dict()

            else:
                res_dict["state"] = session_state.to_dict()

            # Workflow Synchronization & Interruption Check
            active_wf = self._workflow_tracker.get_active_workflow(session_id)
            if active_wf and not active_wf.is_completed and not active_wf.is_cancelled:
                expected_route = payload.get("expected_route")
                if expected_route and curr_page != expected_route:
                    # Navigation mismatch: Mark workflow as INTERRUPTED and save checkpoint
                    checkpoint = JourneyCheckpoint(
                        workflow_id=active_wf.workflow_id,
                        workflow_name=active_wf.workflow_name,
                        step_name=active_wf.current_step,
                        step_index=active_wf.step_index,
                        route_page=prev_page,
                        route_parameters=dict(session_state.current_route_parameters),
                    )
                    self._workflow_tracker.mark_interrupted(
                        session_id=session_id,
                        reason=f"Navigated to '{curr_page}' away from expected '{expected_route}'",
                        checkpoint=checkpoint,
                    )
                    self._journey_store.set_checkpoint(session_id, checkpoint)

            # Measure duration
            duration_ms = round((time.perf_counter() - start_ts) * 1000, 2)

            # Record Transition into Journey Store
            transition = NavigationTransition(
                session_id=session_id,
                conversation_id=session_state.conversation_id,
                workflow_id=active_wf.workflow_id if active_wf else None,
                workflow_step=active_wf.current_step if active_wf else None,
                previous_page=prev_page,
                current_page=curr_page,
                target_page=curr_page,
                navigation_action=event_name,
                triggering_ui_element=payload.get("component_id", payload.get("button_id")),
                triggering_ai_intent=payload.get("ai_intent"),
                ui_transition_chain=ui_chain,
                priority=priority,
                transition_status=TransitionStatus.SUCCESS if res_dict.get("status") == "SUCCESS" else TransitionStatus.FAILED,
                transition_duration=duration_ms,
                trace_id=payload.get("trace_id"),
                request_id=payload.get("request_id"),
                decision_id=payload.get("decision_id"),
                plan_id=payload.get("plan_id"),
                execution_id=payload.get("execution_id"),
                metadata=payload,
            )

            self._journey_store.record_transition(transition)

            # Non-blocking deterministic EventAcknowledgement
            ack = EventAcknowledgement(
                event_id=str(uuid4()),
                event_type=event_name,
                session_id=session_id,
                status=AcknowledgementState.PROCESSED,
            )
            res_dict["acknowledgement"] = ack.to_dict()

            return res_dict

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return diagnostic statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "events_processed_count": self._events_processed_count,
                "thread_safe": True,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose performance metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            message="NavigationSyncManager operational.",
        )
