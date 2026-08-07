"""Core Dialogue Orchestrating Engine for AI Conversation Framework v1.0."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.conversation.conversation_context import (
    AIConversationContext,
    ConversationContextBuilder,
)
from app.conversation.conversation_models import (
    ClarificationType,
    ConversationSnapshot,
    DetectedIntent,
    DialogueState,
    DialogueTurn,
)
from app.conversation.conversation_policy_engine import ConversationPolicyEngine
from app.conversation.conversation_recovery_engine import ConversationRecoveryEngine
from app.conversation.conversation_strategy_engine import ConversationStrategyEngine
from app.conversation.conversation_telemetry import ConversationTelemetryEngine
from app.conversation.conversation_workflow_graph import ConversationWorkflowGraph
from app.conversation.entity_extractor import EntityExtractor
from app.conversation.intent_engine import IntentEngine
from app.conversation.response_manager import ResponseManager
from app.conversation.slot_manager import SlotManager

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ConversationManager"
_COMPONENT_VERSION = "1.0.0"


class ConversationManager:
    """Enterprise thread-safe conversation manager coordinating dialogue turns, understanding, policy governance, and context building."""

    def __init__(
        self,
        intent_engine: IntentEngine | None = None,
        entity_extractor: EntityExtractor | None = None,
        slot_manager: SlotManager | None = None,
        workflow_graph: ConversationWorkflowGraph | None = None,
        policy_engine: ConversationPolicyEngine | None = None,
        strategy_engine: ConversationStrategyEngine | None = None,
        recovery_engine: ConversationRecoveryEngine | None = None,
        response_manager: ResponseManager | None = None,
        context_builder: ConversationContextBuilder | None = None,
        telemetry_engine: ConversationTelemetryEngine | None = None,
    ) -> None:
        self._intent_engine = intent_engine or IntentEngine()
        self._entity_extractor = entity_extractor or EntityExtractor()
        self._slot_manager = slot_manager or SlotManager()
        self._workflow_graph = workflow_graph or ConversationWorkflowGraph()
        self._policy_engine = policy_engine or ConversationPolicyEngine()
        self._strategy_engine = strategy_engine or ConversationStrategyEngine()
        self._recovery_engine = recovery_engine or ConversationRecoveryEngine(self._workflow_graph)
        self._response_manager = response_manager or ResponseManager()
        self._context_builder = context_builder or ConversationContextBuilder(
            workflow_graph=self._workflow_graph,
            slot_manager=self._slot_manager,
        )
        self._telemetry_engine = telemetry_engine or ConversationTelemetryEngine()
        self._turns_history: dict[str, list[DialogueTurn]] = {}
        self._active_intents: dict[str, DetectedIntent] = {}
        self._lock = RLock()
        self._turns_processed_count = 0

    def process_turn(
        self,
        session_id: str,
        utterance: str,
        metadata: dict[str, Any] | None = None,
    ) -> AIConversationContext:
        """Process an incoming user conversation turn and return updated AIConversationContext snapshot."""
        start_ts = time.perf_counter()
        with self._lock:
            self._turns_processed_count += 1
            metadata = metadata or {}
            auth_state = metadata.get("auth_state", "ANONYMOUS")
            conv_id = metadata.get("conversation_id", session_id)

            if session_id not in self._turns_history:
                self._turns_history[session_id] = []

            # 1. Update State to PROCESSING
            self._workflow_graph.transition_to(session_id, DialogueState.PROCESSING, reason="Processing turn")

            # 2. Intent Detection & Strategy Selection
            primary_intent = self._intent_engine.detect_intent(utterance)
            sub_intents = self._intent_engine.detect_sub_intents(utterance)

            if sub_intents:
                all_candidates = [primary_intent] + sub_intents
                selected_intent = self._strategy_engine.prioritize_intents(all_candidates)
            else:
                selected_intent = primary_intent

            self._active_intents[session_id] = selected_intent
            self._telemetry_engine.record_intent_confidence(selected_intent.confidence)

            # 3. Entity Extraction & Slot Filling
            extracted_entities = self._entity_extractor.extract_entities(utterance)
            slot_values_map = self._slot_manager.fill_slots(session_id, extracted_entities)

            # Record turn in history
            turn = DialogueTurn(
                turn_index=len(self._turns_history[session_id]) + 1,
                speaker="USER",
                utterance=utterance,
                detected_intent=selected_intent,
                entities=extracted_entities,
                slots={k: v.value for k, v in slot_values_map.items()},
            )
            self._turns_history[session_id].append(turn)

            # 4. Policy Evaluation
            policy_res = self._policy_engine.evaluate_policy(
                session_id=session_id,
                intent=selected_intent,
                slots={k: v.value for k, v in slot_values_map.items()},
                auth_state=auth_state,
            )

            policy_warnings: list[str] = []
            if not policy_res.is_allowed:
                policy_warnings.append(policy_res.reason)
                if policy_res.required_action == "LOGIN_REQUIRED":
                    self._workflow_graph.transition_to(session_id, DialogueState.AWAITING_CLARIFICATION, reason="Authentication required")
                elif policy_res.required_action == "CONFIRMATION_REQUIRED":
                    self._workflow_graph.transition_to(session_id, DialogueState.AWAITING_CONFIRMATION, reason="Confirmation required")

            # 5. Missing Slot Resolution & Dialogue State Management
            missing_slots = self._slot_manager.get_missing_slots(session_id, selected_intent.intent_name)

            if missing_slots and not policy_warnings:
                self._workflow_graph.transition_to(session_id, DialogueState.AWAITING_SLOT_INPUT, reason="Missing required slots")
                self._telemetry_engine.record_clarification()
            elif not missing_slots and not policy_warnings:
                self._workflow_graph.transition_to(session_id, DialogueState.COMPLETED, reason="All required slots filled")

            # Record checkpoint on completed intent state
            if self._workflow_graph.get_state(session_id) == DialogueState.COMPLETED:
                self._workflow_graph.create_checkpoint(
                    session_id=session_id,
                    active_intent=selected_intent.intent_name,
                    slots={k: v.value for k, v in slot_values_map.items()},
                )

            # 6. Build Context Snapshot
            recent_turns_dicts = [t.to_dict() for t in self._turns_history[session_id][-5:]]
            context = self._context_builder.build_context(
                session_id=session_id,
                conversation_id=conv_id,
                active_intent=selected_intent,
                recent_turns=recent_turns_dicts,
            )

            # Telemetry Latency
            duration_ms = round((time.perf_counter() - start_ts) * 1000, 2)
            self._telemetry_engine.record_turn_latency(duration_ms)

            logger.info("Processed conversation turn for session '%s' [State: %s, Latency: %.2fms]", session_id, context.dialogue_state, duration_ms)
            return context

    def interrupt_conversation(self, session_id: str, reason: str = "USER_INTERRUPT") -> ConversationSnapshot:
        """Interrupt current conversation and record snapshot."""
        with self._lock:
            state = self._workflow_graph.handle_interruption(session_id, triggering_intent=reason)
            ckpt = self._workflow_graph.create_checkpoint(session_id, active_intent=self._active_intents.get(session_id, DetectedIntent()).intent_name)
            turns = self._turns_history.get(session_id, [])
            slots = self._slot_manager.get_slots(session_id)
            return ConversationSnapshot(
                session_id=session_id,
                dialogue_state=state,
                active_intent=self._active_intents.get(session_id),
                confirmed_slots={k: v.value for k, v in slots.items() if v.is_validated},
                turns=turns,
                checkpoint=ckpt,
            )

    def resume_conversation(self, session_id: str) -> AIConversationContext:
        """Resume an interrupted conversation from latest checkpoint."""
        with self._lock:
            ckpt = self._recovery_engine.recover_to_checkpoint(session_id)
            active_intent = self._active_intents.get(session_id)
            recent_turns = [t.to_dict() for t in self._turns_history.get(session_id, [])[-5:]]
            return self._context_builder.build_context(
                session_id=session_id,
                active_intent=active_intent,
                recent_turns=recent_turns,
            )

    def get_conversation_summary(self, session_id: str) -> str:
        """Get text summary of session conversation."""
        with self._lock:
            ctx = self._context_builder.build_context(session_id, active_intent=self._active_intents.get(session_id))
            return ctx.summary_text

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "turns_processed_count": self._turns_processed_count,
                "active_sessions_tracked": len(self._turns_history),
                "telemetry": self._telemetry_engine.statistics(),
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


EnterpriseConversationManager = ConversationManager
