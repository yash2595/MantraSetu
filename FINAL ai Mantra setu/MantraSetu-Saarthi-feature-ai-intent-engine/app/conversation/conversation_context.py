"""Conversational Context Snapshot Builder for Prompt & AI Orchestrator Integration v1.0."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.conversation.conversation_models import DetectedIntent, DialogueState
from app.conversation.conversation_workflow_graph import ConversationWorkflowGraph
from app.conversation.slot_manager import SlotManager
from app.navigation.context_builder import AINavigationContext, NavigationContextBuilder

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ConversationContextBuilder"
_COMPONENT_VERSION = "1.0.0"


@dataclass(frozen=True)
class AIConversationContext:
    """Complete immutable conversational context snapshot injected into Prompt Builder and AI Orchestrator."""

    session_id: str
    conversation_id: str
    dialogue_state: DialogueState
    active_intent: DetectedIntent | None
    confirmed_slots: dict[str, Any]
    pending_slots: list[str]
    recent_turns: list[dict[str, Any]]
    clarification_needed: bool = False
    clarification_question: str | None = None
    confirmation_needed: bool = False
    confirmation_prompt: str | None = None
    summary_text: str = ""
    navigation_context: dict[str, Any] = field(default_factory=dict)
    policy_warnings: list[str] = field(default_factory=list)
    recovery_attempts: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "dialogue_state": str(self.dialogue_state),
            "active_intent": self.active_intent.to_dict() if self.active_intent else None,
            "confirmed_slots": dict(self.confirmed_slots),
            "pending_slots": list(self.pending_slots),
            "recent_turns": list(self.recent_turns),
            "clarification_needed": self.clarification_needed,
            "clarification_question": self.clarification_question,
            "confirmation_needed": self.confirmation_needed,
            "confirmation_prompt": self.confirmation_prompt,
            "summary_text": self.summary_text,
            "navigation_context": dict(self.navigation_context),
            "policy_warnings": list(self.policy_warnings),
            "recovery_attempts": self.recovery_attempts,
        }


class ConversationContextBuilder:
    """Builder generating dynamic AIConversationContext snapshots integrating Sprint 1 NavigationContextBuilder via public interface."""

    def __init__(
        self,
        workflow_graph: ConversationWorkflowGraph | None = None,
        slot_manager: SlotManager | None = None,
        nav_context_builder: NavigationContextBuilder | None = None,
    ) -> None:
        self._workflow_graph = workflow_graph or ConversationWorkflowGraph()
        self._slot_manager = slot_manager or SlotManager()
        self._nav_context_builder = nav_context_builder or NavigationContextBuilder()
        self._lock = RLock()
        self._snapshots_built_count = 0

    def build_context(
        self,
        session_id: str,
        conversation_id: str = "",
        active_intent: DetectedIntent | None = None,
        recent_turns: list[dict[str, Any]] | None = None,
    ) -> AIConversationContext:
        """Assemble complete runtime AIConversationContext combining dialogue state, slots, and Sprint 1 navigation context."""
        with self._lock:
            self._snapshots_built_count += 1
            dialogue_state = self._workflow_graph.get_state(session_id)

            # Fetch slot information
            slot_objects = self._slot_manager.get_slots(session_id)
            confirmed_slots = {k: v.value for k, v in slot_objects.items() if v.is_validated and v.value is not None}

            pending_slots: list[str] = []
            if active_intent:
                missing_reqs = self._slot_manager.get_missing_slots(session_id, active_intent.intent_name)
                pending_slots = [r.slot_name for r in missing_reqs]

            # Fetch Sprint 1 Navigation Context via public read-only interface
            nav_ctx_dict = {}
            try:
                nav_ctx: AINavigationContext = self._nav_context_builder.build_context(session_id, conversation_id)
                nav_ctx_dict = nav_ctx.to_dict()
            except Exception as e:
                logger.warning("Failed to fetch Sprint 1 NavigationContext for session '%s': %s", session_id, e)

            # Build summary text
            intent_str = active_intent.intent_name if active_intent else "UNKNOWN"
            slots_str = ", ".join(f"{k}: {v}" for k, v in confirmed_slots.items()) if confirmed_slots else "None"
            summary_text = f"Dialogue State: {dialogue_state}. Active Intent: {intent_str}. Confirmed Slots: [{slots_str}]."

            context = AIConversationContext(
                session_id=session_id,
                conversation_id=conversation_id or session_id,
                dialogue_state=dialogue_state,
                active_intent=active_intent,
                confirmed_slots=confirmed_slots,
                pending_slots=pending_slots,
                recent_turns=list(recent_turns or []),
                clarification_needed=(dialogue_state == DialogueState.AWAITING_CLARIFICATION or bool(pending_slots)),
                confirmation_needed=(dialogue_state == DialogueState.AWAITING_CONFIRMATION),
                summary_text=summary_text,
                navigation_context=nav_ctx_dict,
            )

            logger.debug("Built AIConversationContext snapshot for session '%s' [State: %s]", session_id, dialogue_state)
            return context

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose builder operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "snapshots_built_count": self._snapshots_built_count,
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
