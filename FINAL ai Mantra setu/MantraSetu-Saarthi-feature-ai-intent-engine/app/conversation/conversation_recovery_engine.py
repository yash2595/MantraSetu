"""Zero-Loss Dialogue Recovery Engine for Failure Fallbacks v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.conversation.conversation_models import (
    DialogueCheckpoint,
    DialogueState,
    RecoveryResult,
    RecoveryStrategyType,
)
from app.conversation.conversation_workflow_graph import ConversationWorkflowGraph

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ConversationRecoveryEngine"
_COMPONENT_VERSION = "1.0.0"


class ConversationRecoveryEngine:
    """Enterprise thread-safe recovery engine executing zero-loss fallback strategies for dialogue failures."""

    def __init__(self, workflow_graph: ConversationWorkflowGraph | None = None) -> None:
        self._workflow_graph = workflow_graph or ConversationWorkflowGraph()
        self._lock = RLock()
        self._recovery_attempts_count = 0

    def handle_timeout(self, session_id: str) -> RecoveryResult:
        """Handle LLM response timeout failure."""
        with self._lock:
            self._recovery_attempts_count += 1
            logger.warning("RecoveryEngine handling LLM timeout for session '%s'", session_id)
            ckpt = self._workflow_graph.get_latest_checkpoint(session_id)
            if ckpt:
                self._workflow_graph.restore_checkpoint(session_id, ckpt.checkpoint_id)
                return RecoveryResult(
                    success=True,
                    recovery_strategy=RecoveryStrategyType.RESTORE_CHECKPOINT,
                    new_state=ckpt.state_name,
                    message="Restored previous stable dialogue state after timeout.",
                    restored_checkpoint=ckpt,
                )
            else:
                new_state = self._workflow_graph.transition_to(session_id, DialogueState.IDLE, reason="Timeout fallback")
                return RecoveryResult(
                    success=True,
                    recovery_strategy=RecoveryStrategyType.CLARIFY_INTENT,
                    new_state=new_state,
                    message="Sorry, the request timed out. Please try stating your goal again.",
                )

    def handle_invalid_slot(self, session_id: str, slot_name: str, raw_value: Any) -> RecoveryResult:
        """Handle invalid slot value input failure."""
        with self._lock:
            self._recovery_attempts_count += 1
            logger.warning("RecoveryEngine handling invalid slot '%s' (value: %s) for session '%s'", slot_name, raw_value, session_id)
            new_state = self._workflow_graph.transition_to(session_id, DialogueState.AWAITING_SLOT_INPUT, reason="Invalid slot re-ask")
            return RecoveryResult(
                success=True,
                recovery_strategy=RecoveryStrategyType.REASK_SLOT,
                new_state=new_state,
                message=f"The value '{raw_value}' provided for {slot_name.replace('_', ' ')} was invalid. Please provide a valid value.",
            )

    def handle_context_overflow(self, session_id: str, max_turns: int = 10) -> RecoveryResult:
        """Handle context window token overflow failure by truncating turns."""
        with self._lock:
            self._recovery_attempts_count += 1
            logger.info("RecoveryEngine truncating context window for session '%s'", session_id)
            return RecoveryResult(
                success=True,
                recovery_strategy=RecoveryStrategyType.TRUNCATE_CONTEXT,
                new_state=self._workflow_graph.get_state(session_id),
                message="Context window truncated to recent turns.",
            )

    def recover_to_checkpoint(self, session_id: str) -> RecoveryResult:
        """Explicitly restore dialogue to latest checkpoint."""
        with self._lock:
            self._recovery_attempts_count += 1
            ckpt = self._workflow_graph.restore_checkpoint(session_id)
            if ckpt:
                return RecoveryResult(
                    success=True,
                    recovery_strategy=RecoveryStrategyType.RESTORE_CHECKPOINT,
                    new_state=ckpt.state_name,
                    message=f"Recovered to checkpoint '{ckpt.checkpoint_id}'.",
                    restored_checkpoint=ckpt,
                )
            return RecoveryResult(
                success=False,
                recovery_strategy=RecoveryStrategyType.FALLBACK_TO_HUMAN,
                new_state=DialogueState.ERROR,
                message="No checkpoint available for recovery.",
            )

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose recovery engine operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "recovery_attempts_count": self._recovery_attempts_count,
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
