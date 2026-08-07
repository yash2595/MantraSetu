"""Deterministic State Machine Governing Dialogue State Transitions & Checkpoints for v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.conversation.conversation_models import DialogueCheckpoint, DialogueState

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ConversationWorkflowGraph"
_COMPONENT_VERSION = "1.0.0"


class ConversationWorkflowGraph:
    """Enterprise thread-safe state machine managing dialogue transitions, checkpoints, and interruptions."""

    # Valid state transition graph map
    _ALLOWED_TRANSITIONS: dict[DialogueState, set[DialogueState]] = {
        DialogueState.IDLE: {DialogueState.LISTENING, DialogueState.PROCESSING, DialogueState.ERROR},
        DialogueState.LISTENING: {DialogueState.PROCESSING, DialogueState.INTERRUPTED, DialogueState.ERROR},
        DialogueState.PROCESSING: {
            DialogueState.AWAITING_SLOT_INPUT,
            DialogueState.AWAITING_CLARIFICATION,
            DialogueState.AWAITING_CONFIRMATION,
            DialogueState.COMPLETED,
            DialogueState.INTERRUPTED,
            DialogueState.ESCALATED,
            DialogueState.ERROR,
        },
        DialogueState.AWAITING_SLOT_INPUT: {DialogueState.LISTENING, DialogueState.PROCESSING, DialogueState.INTERRUPTED, DialogueState.ERROR},
        DialogueState.AWAITING_CLARIFICATION: {DialogueState.LISTENING, DialogueState.PROCESSING, DialogueState.INTERRUPTED, DialogueState.ERROR},
        DialogueState.AWAITING_CONFIRMATION: {DialogueState.COMPLETED, DialogueState.PROCESSING, DialogueState.INTERRUPTED, DialogueState.ERROR},
        DialogueState.COMPLETED: {DialogueState.IDLE, DialogueState.LISTENING, DialogueState.PROCESSING},
        DialogueState.INTERRUPTED: {DialogueState.IDLE, DialogueState.LISTENING, DialogueState.PROCESSING, DialogueState.AWAITING_SLOT_INPUT},
        DialogueState.ESCALATED: {DialogueState.IDLE, DialogueState.ERROR},
        DialogueState.ERROR: {DialogueState.IDLE, DialogueState.LISTENING},
    }

    def __init__(self) -> None:
        self._session_states: dict[str, DialogueState] = {}
        self._checkpoints: dict[str, dict[str, DialogueCheckpoint]] = {}
        self._lock = RLock()
        self._transition_count = 0
        self._interruption_count = 0

    def get_state(self, session_id: str) -> DialogueState:
        """Retrieve active dialogue state for a session."""
        with self._lock:
            return self._session_states.get(session_id, DialogueState.IDLE)

    def transition_to(self, session_id: str, target_state: DialogueState, reason: str = "") -> DialogueState:
        """Transition session to target_state if transition is valid in the state graph."""
        with self._lock:
            current = self.get_state(session_id)
            allowed = self._ALLOWED_TRANSITIONS.get(current, set())

            if target_state in allowed or target_state == current or target_state == DialogueState.ERROR:
                self._session_states[session_id] = target_state
                self._transition_count += 1
                logger.debug("Session '%s' dialogue state transitioned %s -> %s [Reason: %s]", session_id, current, target_state, reason)
                return target_state
            else:
                logger.warning("Invalid dialogue state transition %s -> %s for session '%s'", current, target_state, session_id)
                return current

    def create_checkpoint(self, session_id: str, active_intent: str | None = None, slots: dict[str, Any] | None = None) -> DialogueCheckpoint:
        """Create a state checkpoint for the active session."""
        with self._lock:
            current = self.get_state(session_id)
            ckpt = DialogueCheckpoint(
                state_name=current,
                confirmed_slots=dict(slots or {}),
                active_intent=active_intent,
            )
            if session_id not in self._checkpoints:
                self._checkpoints[session_id] = {}
            self._checkpoints[session_id][ckpt.checkpoint_id] = ckpt
            logger.info("Created DialogueCheckpoint '%s' for session '%s'", ckpt.checkpoint_id, session_id)
            return ckpt

    def get_latest_checkpoint(self, session_id: str) -> DialogueCheckpoint | None:
        """Retrieve most recent checkpoint for session."""
        with self._lock:
            ckpts = self._checkpoints.get(session_id, {})
            if not ckpts:
                return None
            return list(ckpts.values())[-1]

    def restore_checkpoint(self, session_id: str, checkpoint_id: str | None = None) -> DialogueCheckpoint | None:
        """Restore session state to a saved checkpoint."""
        with self._lock:
            ckpts = self._checkpoints.get(session_id, {})
            if not ckpts:
                return None

            if checkpoint_id and checkpoint_id in ckpts:
                ckpt = ckpts[checkpoint_id]
            else:
                ckpt = list(ckpts.values())[-1]

            self._session_states[session_id] = ckpt.state_name
            logger.info("Restored DialogueCheckpoint '%s' for session '%s'", ckpt.checkpoint_id, session_id)
            return ckpt

    def handle_interruption(self, session_id: str, triggering_intent: str = "") -> DialogueState:
        """Handle dialogue interruption event."""
        with self._lock:
            self._interruption_count += 1
            return self.transition_to(session_id, DialogueState.INTERRUPTED, reason=f"Triggered by intent: {triggering_intent}")

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose workflow graph operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "active_sessions_tracked": len(self._session_states),
                "total_transitions": self._transition_count,
                "total_interruptions": self._interruption_count,
                "checkpoints_cached": sum(len(c) for c in self._checkpoints.values()),
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
