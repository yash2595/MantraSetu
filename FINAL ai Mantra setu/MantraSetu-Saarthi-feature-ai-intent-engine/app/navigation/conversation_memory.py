"""Persistent Conversation Memory Manager for MantraSetu AgentOS.

Architecture Layer: Conversational Knowledge
Ownership: Conversation history, extracted entities, slot resolution, and resume checkpoints ONLY.
          Does NOT own runtime UI state (→ NavigationStateStore) or static metadata (→ RouteRegistry).
Thread Safety: RLock-protected with configurable memory growth limits and automatic pruning.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ConversationMemoryManager"
_COMPONENT_VERSION = "4.1"

# Default configurable memory limits — prevents unbounded growth
_DEFAULT_MAX_HISTORY = 200
_DEFAULT_MAX_ENTITY_HISTORY = 500
_DEFAULT_MAX_SLOT_HISTORY = 200
_DEFAULT_MAX_SUMMARY_HISTORY = 50


@dataclass
class ConversationMemorySnapshot:
    """Mutable snapshot of a user's conversational knowledge state.

    CRITICAL: This stores conversational knowledge ONLY.
    Runtime DOM/navigation state belongs in NavigationSessionState.
    Static route metadata belongs in RouteRegistry.
    """

    session_id: str
    conversation_id: str
    # Dialogue turns: list of {role, content, timestamp} dicts
    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    # High-level user goals extracted from conversation
    user_goals: list[str] = field(default_factory=list)
    # AI-generated questions and user answers
    ai_questions: list[str] = field(default_factory=list)
    user_answers: list[str] = field(default_factory=list)
    # Domain entity extraction results
    extracted_entities: dict[str, Any] = field(default_factory=dict)
    entity_history: list[dict[str, Any]] = field(default_factory=list)
    # Domain-specific selections
    selected_services: list[str] = field(default_factory=list)
    selected_pujas: list[str] = field(default_factory=list)
    selected_pandits: list[str] = field(default_factory=list)
    booking_progress: float = 0.0
    # Slot resolution tracking
    confirmed_inputs: dict[str, Any] = field(default_factory=dict)
    pending_inputs: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    intent_history: list[str] = field(default_factory=list)
    slot_history: list[dict[str, Any]] = field(default_factory=list)
    resolved_slots: set[str] = field(default_factory=set)
    # Workflow interruption and resumption checkpoints
    workflow_interruptions: list[dict[str, Any]] = field(default_factory=list)
    resume_checkpoints: dict[str, str] = field(default_factory=dict)
    # Rolling context summaries
    summaries: list[str] = field(default_factory=list)
    context_summary: str = ""
    # AI confidence tracking
    confidence_history: list[float] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Return a defensive copy as a plain dict."""
        return {
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "conversation_history": list(self.conversation_history),
            "user_goals": list(self.user_goals),
            "ai_questions": list(self.ai_questions),
            "user_answers": list(self.user_answers),
            "extracted_entities": dict(self.extracted_entities),
            "entity_history": list(self.entity_history),
            "selected_services": list(self.selected_services),
            "selected_pujas": list(self.selected_pujas),
            "selected_pandits": list(self.selected_pandits),
            "booking_progress": self.booking_progress,
            "confirmed_inputs": dict(self.confirmed_inputs),
            "pending_inputs": list(self.pending_inputs),
            "missing_information": list(self.missing_information),
            "intent_history": list(self.intent_history),
            "slot_history": list(self.slot_history),
            "resolved_slots": list(self.resolved_slots),
            "workflow_interruptions": list(self.workflow_interruptions),
            "resume_checkpoints": dict(self.resume_checkpoints),
            "summaries": list(self.summaries),
            "context_summary": self.context_summary,
            "confidence_history": list(self.confidence_history),
            "updated_at": self.updated_at,
        }


class ConversationMemoryManager:
    """Thread-safe manager for session conversational knowledge and workflow resume points.

    Configurable memory limits prevent unbounded growth.
    Oldest entries are pruned automatically when limits are exceeded.

    Public API (backward-compatible):
        get_memory(), record_turn(), record_interruption(), update_summary(),
        clear_memory(), statistics(), health()
    """

    def __init__(
        self,
        max_history: int = _DEFAULT_MAX_HISTORY,
        max_entity_history: int = _DEFAULT_MAX_ENTITY_HISTORY,
        max_slot_history: int = _DEFAULT_MAX_SLOT_HISTORY,
        max_summary_history: int = _DEFAULT_MAX_SUMMARY_HISTORY,
    ) -> None:
        self._memories: dict[str, ConversationMemorySnapshot] = {}
        self._lock = RLock()
        self._record_count = 0
        self._started_at = datetime.now(timezone.utc).isoformat()

        # Configurable growth limits
        self._max_history = max_history
        self._max_entity_history = max_entity_history
        self._max_slot_history = max_slot_history
        self._max_summary_history = max_summary_history

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_or_create(self, session_id: str, conversation_id: str = "") -> ConversationMemorySnapshot:
        """Get or initialize memory snapshot (must be called under lock)."""
        if session_id not in self._memories:
            self._memories[session_id] = ConversationMemorySnapshot(
                session_id=session_id,
                conversation_id=conversation_id or f"conv_{session_id}",
            )
        return self._memories[session_id]

    @staticmethod
    def _prune(collection: list[Any], max_len: int) -> None:
        """Prune oldest entries from a list to enforce max_len limit."""
        while len(collection) > max_len:
            collection.pop(0)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_memory(self, session_id: str, conversation_id: str = "") -> ConversationMemorySnapshot:
        """Get or initialize conversational memory for a session. Complexity: O(1)."""
        with self._lock:
            return self._get_or_create(session_id, conversation_id)

    def record_turn(
        self,
        session_id: str,
        user_input: str | None = None,
        ai_response: str | None = None,
        intent: str | None = None,
        entities: dict[str, Any] | None = None,
        confidence: float | None = None,
    ) -> ConversationMemorySnapshot:
        """Record a conversation turn and merge extracted entity data.

        Bounded by max_history — oldest turns are pruned when limit is exceeded.
        """
        with self._lock:
            mem = self._get_or_create(session_id)
            timestamp = datetime.now(timezone.utc).isoformat()

            if user_input:
                mem.conversation_history.append({"role": "user", "content": user_input, "timestamp": timestamp})
                mem.user_answers.append(user_input)
                self._prune(mem.conversation_history, self._max_history)
            if ai_response:
                mem.conversation_history.append({"role": "assistant", "content": ai_response, "timestamp": timestamp})
                mem.ai_questions.append(ai_response)
                self._prune(mem.conversation_history, self._max_history)
            if intent:
                mem.intent_history.append(intent)
            if confidence is not None:
                mem.confidence_history.append(confidence)

            if entities:
                mem.extracted_entities.update(entities)
                mem.confirmed_inputs.update(entities)
                mem.entity_history.append({"timestamp": timestamp, "entities": dict(entities)})
                self._prune(mem.entity_history, self._max_entity_history)
                for k in entities.keys():
                    mem.resolved_slots.add(k)
                mem.slot_history.append({"timestamp": timestamp, "slots": list(entities.keys())})
                self._prune(mem.slot_history, self._max_slot_history)

            self._record_count += 1
            mem.updated_at = timestamp
            logger.debug(
                "Conversation turn recorded [operation=record_turn, session_id=%s, history_len=%d, intent=%s]",
                session_id,
                len(mem.conversation_history),
                intent,
            )
            return mem

    def record_interruption(
        self,
        session_id: str,
        workflow_name: str,
        step_name: str,
        reason: str = "",
    ) -> None:
        """Record a workflow interruption checkpoint for later resumption."""
        with self._lock:
            mem = self._get_or_create(session_id)
            interruption = {
                "workflow_name": workflow_name,
                "step_name": step_name,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            mem.workflow_interruptions.append(interruption)
            mem.resume_checkpoints[workflow_name] = step_name
            mem.updated_at = datetime.now(timezone.utc).isoformat()
            logger.info(
                "Workflow interruption recorded [operation=record_interruption, session_id=%s, workflow=%s, step=%s, reason=%s]",
                session_id,
                workflow_name,
                step_name,
                reason,
            )

    def update_summary(self, session_id: str, summary: str) -> None:
        """Update the rolling conversation context summary.

        Summary history is bounded by max_summary_history.
        """
        with self._lock:
            mem = self._get_or_create(session_id)
            mem.context_summary = summary
            mem.summaries.append(summary)
            self._prune(mem.summaries, self._max_summary_history)
            mem.updated_at = datetime.now(timezone.utc).isoformat()

    def clear_memory(self, session_id: str) -> None:
        """Remove all conversation memory for a session."""
        with self._lock:
            self._memories.pop(session_id, None)

    def statistics(self) -> dict[str, Any]:
        """Return read-only enterprise diagnostics for ConversationMemoryManager."""
        with self._lock:
            total_turns = sum(len(m.conversation_history) for m in self._memories.values())
            total_slots = sum(len(m.resolved_slots) for m in self._memories.values())
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "active_memories_count": len(self._memories),
                "total_record_count": self._record_count,
                "total_conversation_turns": total_turns,
                "total_resolved_slots": total_slots,
                "max_history": self._max_history,
                "max_entity_history": self._max_entity_history,
                "max_slot_history": self._max_slot_history,
                "max_summary_history": self._max_summary_history,
                "sessions": [m.session_id for m in self._memories.values()],
            }

    def health(self) -> dict[str, Any]:
        """Return read-only health status for ConversationMemoryManager."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "status": "HEALTHY",
                "active_memories": len(self._memories),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
