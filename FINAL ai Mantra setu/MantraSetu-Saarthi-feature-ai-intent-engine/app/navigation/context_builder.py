"""Dynamic Navigation Context Builder for MantraSetu AgentOS v4.1."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any

from app.navigation.context_cache import ContextCache
from app.navigation.conversation_memory import (
    ConversationMemoryManager,
    ConversationMemorySnapshot,
)
from app.navigation.journey_store import NavigationJourneyStore
from app.navigation.registry import RouteRegistry
from app.navigation.state_store import NavigationSessionState, NavigationStateStore
from app.navigation.ui_registry import UIRegistry
from app.navigation.workflow_tracker import WorkflowTracker

logger = logging.getLogger(__name__)


@dataclass
class AINavigationContext:
    """Complete immutable navigation context snapshot injected into AI & reasoning engines."""

    session_id: str
    conversation_id: str
    current_page: str
    previous_page: str | None
    navigation_history: list[str]
    current_route_parameters: dict[str, Any]
    pending_navigation: str | None
    pending_action: str | None
    active_workflow: str | None
    workflow_step: str | None
    auth_state: str
    last_user_intent: str | None
    visited_pages: list[str]
    recent_navigation_stack: list[str]
    breadcrumb_trail: list[str]
    supported_ai_actions: list[str]
    page_metadata: dict[str, Any] = field(default_factory=dict)
    ui_elements: list[dict[str, Any]] = field(default_factory=list)
    memory_summary: dict[str, Any] = field(default_factory=dict)

    # Enterprise Journey Subsystem Extensions (v4.1)
    journey_summary_text: str = ""
    navigation_pattern: list[str] = field(default_factory=list)
    recent_navigation_behaviour: dict[str, Any] = field(default_factory=dict)
    predicted_next_page: str | None = None
    workflow_completion_percentage: float = 0.0
    last_transition_reason: str | None = None
    current_navigation_depth: int = 1
    recent_ui_actions: list[dict[str, Any]] = field(default_factory=list)
    current_journey_summary: dict[str, Any] = field(default_factory=dict)
    journey_timeline: list[dict[str, Any]] = field(default_factory=list)
    journey_graph_summary: dict[str, Any] = field(default_factory=dict)
    navigation_frequency: dict[str, int] = field(default_factory=dict)
    recent_transitions: list[dict[str, Any]] = field(default_factory=list)
    last_successful_navigation: str | None = None
    last_failed_navigation: str | None = None
    resume_point: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert context snapshot into serializable dictionary."""
        return {
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "current_page": self.current_page,
            "previous_page": self.previous_page,
            "navigation_history": list(self.navigation_history),
            "current_route_parameters": dict(self.current_route_parameters),
            "pending_navigation": self.pending_navigation,
            "pending_action": self.pending_action,
            "active_workflow": self.active_workflow,
            "workflow_step": self.workflow_step,
            "auth_state": self.auth_state,
            "last_user_intent": self.last_user_intent,
            "visited_pages": list(self.visited_pages),
            "recent_navigation_stack": list(self.recent_navigation_stack),
            "breadcrumb_trail": list(self.breadcrumb_trail),
            "supported_ai_actions": list(self.supported_ai_actions),
            "page_metadata": dict(self.page_metadata),
            "ui_elements": list(self.ui_elements),
            "memory_summary": dict(self.memory_summary),
            "journey_summary_text": self.journey_summary_text,
            "navigation_pattern": list(self.navigation_pattern),
            "recent_navigation_behaviour": dict(self.recent_navigation_behaviour),
            "predicted_next_page": self.predicted_next_page,
            "workflow_completion_percentage": self.workflow_completion_percentage,
            "last_transition_reason": self.last_transition_reason,
            "current_navigation_depth": self.current_navigation_depth,
            "recent_ui_actions": list(self.recent_ui_actions),
            "current_journey_summary": dict(self.current_journey_summary),
            "journey_timeline": list(self.journey_timeline),
            "journey_graph_summary": dict(self.journey_graph_summary),
            "navigation_frequency": dict(self.navigation_frequency),
            "recent_transitions": list(self.recent_transitions),
            "last_successful_navigation": self.last_successful_navigation,
            "last_failed_navigation": self.last_failed_navigation,
            "resume_point": dict(self.resume_point) if self.resume_point else None,
        }


class NavigationContextBuilder:
    """Builder generating dynamic navigation context snapshots from foundation stores and Journey subsystem."""

    def __init__(
        self,
        state_store: NavigationStateStore | None = None,
        registry: RouteRegistry | None = None,
        workflow_tracker: WorkflowTracker | None = None,
        memory_manager: ConversationMemoryManager | None = None,
        ui_registry: UIRegistry | None = None,
        context_cache: ContextCache | None = None,
        journey_store: NavigationJourneyStore | None = None,
    ) -> None:
        self._state_store = state_store or NavigationStateStore()
        self._registry = registry or RouteRegistry()
        self._workflow_tracker = workflow_tracker or WorkflowTracker(self._state_store)
        self._memory_manager = memory_manager or ConversationMemoryManager()
        self._ui_registry = ui_registry or UIRegistry()
        self._context_cache = context_cache or ContextCache(version="4.1")
        self._journey_store = journey_store or NavigationJourneyStore()
        self._lock = threading.RLock()

    def build_context(self, session_id: str, conversation_id: str = "") -> AINavigationContext:
        """Dynamically assemble runtime AINavigationContext snapshot using all foundation sources and Journey subsystem."""
        with self._lock:
            # 1. Fetch Session State from NavigationStateStore
            session_state: NavigationSessionState = self._state_store.get_state(session_id)
            current_page = session_state.current_page or "/"

            # 2. Check Static Route Metadata from RouteRegistry / ContextCache
            cache_key = f"route_meta:{current_page}"
            page_meta = self._context_cache.get(cache_key)
            if page_meta is None:
                current_node = self._registry.match_path(current_page)
                page_meta = dict(current_node.metadata) if current_node and current_node.metadata else {}
                self._context_cache.set(cache_key, page_meta)

            breadcrumb = page_meta.get("breadcrumb", [current_page])
            actions = page_meta.get("supported_ai_actions", ["NAVIGATE"])

            # 3. Active Workflow Resolution
            wf = self._workflow_tracker.get_active_workflow(session_id)
            if wf and not wf.is_completed and not wf.is_cancelled:
                active_wf_name = wf.workflow_name
                active_wf_step = wf.current_step
            else:
                active_wf_name = session_state.active_workflow
                active_wf_step = session_state.workflow_step

            # 4. Fetch Conversational Memory from ConversationMemoryManager
            conv_id = conversation_id or session_state.conversation_id or session_id
            memory_snap: ConversationMemorySnapshot = self._memory_manager.get_memory(session_id)
            memory_summary = {
                "user_goals": list(memory_snap.user_goals),
                "extracted_entities": dict(memory_snap.extracted_entities),
                "confirmed_inputs": dict(memory_snap.confirmed_inputs),
                "pending_inputs": list(memory_snap.pending_inputs),
                "intent_history": list(memory_snap.intent_history[-5:]),
            }

            # 5. Fetch UI Components for Route from UIRegistry
            ui_elems_raw = self._ui_registry.get_elements_by_page(current_page)
            ui_elements = [
                {
                    "element_id": elem.element_id,
                    "component_type": str(elem.component_type),
                    "label": elem.semantic_label,
                    "is_visible": elem.is_visible,
                    "is_enabled": elem.is_enabled,
                }
                for elem in ui_elems_raw
            ]

            # 6. Fetch Journey Subsystem Context
            journey = self._journey_store.get_journey(session_id)
            graph = self._journey_store.get_graph(session_id)
            timeline = self._journey_store.get_timeline(session_id)

            # Predictions
            probable_next = graph.get_probable_next_destinations(current_page, limit=1)
            predicted_next_page = probable_next[0].route if probable_next else None

            # Transitions
            recent_t_objects = timeline.get_all_transitions()[-5:]
            recent_transitions = [t.to_dict() for t in recent_t_objects]

            last_succ_t = timeline.get_last_successful_transition()
            last_fail_t = timeline.get_last_failed_transition()

            last_succ_page = last_succ_t.current_page if last_succ_t else session_state.last_successful_page
            last_fail_page = last_fail_t.current_page if last_fail_t else session_state.last_failed_navigation

            checkpoint = journey.resume_checkpoint or (wf.checkpoint if wf else None)
            resume_point_dict = checkpoint.to_dict() if checkpoint else None

            # Deterministic LLM Summary Text Generation
            path_str = " → ".join(session_state.navigation_history[-5:])
            if active_wf_name:
                if wf and wf.is_interrupted:
                    summary_text = (
                        f"User navigated {path_str}. Workflow '{active_wf_name}' interrupted "
                        f"during step '{active_wf_step}'. Resume checkpoint available."
                    )
                else:
                    summary_text = (
                        f"User navigated {path_str}. Active workflow '{active_wf_name}' "
                        f"at step '{active_wf_step}'."
                    )
            else:
                summary_text = f"User navigated {path_str}."

            context = AINavigationContext(
                session_id=session_id,
                conversation_id=conv_id,
                current_page=current_page,
                previous_page=session_state.previous_page,
                navigation_history=list(session_state.navigation_history),
                current_route_parameters=dict(session_state.current_route_parameters),
                pending_navigation=session_state.pending_navigation,
                pending_action=session_state.pending_action,
                active_workflow=active_wf_name,
                workflow_step=active_wf_step,
                auth_state=str(session_state.auth_state),
                last_user_intent=session_state.last_user_intent,
                visited_pages=list(session_state.visited_pages),
                recent_navigation_stack=session_state.navigation_history[-5:],
                breadcrumb_trail=list(breadcrumb),
                supported_ai_actions=list(actions),
                page_metadata=dict(page_meta),
                ui_elements=ui_elements,
                memory_summary=memory_summary,
                # Enterprise Extensions
                journey_summary_text=summary_text,
                navigation_pattern=session_state.navigation_history[-5:],
                recent_navigation_behaviour={"visited_count": len(session_state.visited_pages)},
                predicted_next_page=predicted_next_page,
                workflow_completion_percentage=graph.predict_workflow_completion(active_wf_name or "", active_wf_step or "") if active_wf_name else 0.0,
                last_transition_reason=recent_t_objects[-1].navigation_action if recent_t_objects else None,
                current_navigation_depth=len(session_state.navigation_history),
                recent_ui_actions=[{"action": t.navigation_action, "ui_element": t.triggering_ui_element} for t in recent_t_objects if t.triggering_ui_element],
                current_journey_summary={"total_transitions": len(journey.transitions), "is_archived": journey.is_archived},
                journey_timeline=[t.to_dict() for t in timeline.get_all_transitions()[-10:]],
                journey_graph_summary=graph.statistics(),
                navigation_frequency=dict(session_state.navigation_frequency),
                recent_transitions=recent_transitions,
                last_successful_navigation=last_succ_page,
                last_failed_navigation=last_fail_page,
                resume_point=resume_point_dict,
            )

            logger.debug("Built dynamic AINavigationContext snapshot for session '%s'", session_id)
            return context
