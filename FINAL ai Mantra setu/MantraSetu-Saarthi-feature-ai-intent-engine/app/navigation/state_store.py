"""Enterprise thread-safe Navigation State Store for MantraSetu AgentOS.

Architecture Layer: Runtime Session State
Ownership: Runtime navigation and UI state ONLY.
          Does NOT own conversation memory, entity slots, or static route metadata.
Thread Safety: RLock-protected. All public mutations are atomic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "NavigationStateStore"
_COMPONENT_VERSION = "4.1"
_MAX_NAVIGATION_HISTORY = 100


@dataclass
class NavigationSessionState:
    """Mutable runtime snapshot for an active user navigation session.

    CRITICAL: This tracks DOM/navigation runtime state ONLY.
    Conversational knowledge (intents, entities, slots) belongs in ConversationMemoryManager.
    """

    session_id: str
    conversation_id: str = ""
    # Current navigation position
    current_page: str = "/"
    previous_page: str | None = None
    # UI focus state
    current_component: str | None = None
    current_section: str | None = None
    current_modal: str | None = None
    current_tab: str | None = None
    focused_input: str | None = None
    scroll_position: int = 0
    selected_card: str | None = None
    selected_table_row: str | None = None
    # Route parameters
    current_route_parameters: dict[str, Any] = field(default_factory=dict)
    # Pending directives
    pending_navigation: str | None = None
    pending_action: str | None = None
    # Workflow tracking (runtime only — no step logic)
    active_workflow: str | None = None
    workflow_step: str | None = None
    # Navigation history (bounded to _MAX_NAVIGATION_HISTORY)
    navigation_history: list[str] = field(default_factory=lambda: ["/"])
    visited_pages: set[str] = field(default_factory=lambda: {"/"})
    navigation_frequency: dict[str, int] = field(default_factory=lambda: {"/": 1})
    breadcrumb_trail: list[str] = field(default_factory=lambda: ["Home"])
    # Undo / redo stacks (bounded)
    undo_stack: list[str] = field(default_factory=list)
    redo_stack: list[str] = field(default_factory=list)
    favorite_routes: list[str] = field(default_factory=list)
    workflow_checkpoints: dict[str, str] = field(default_factory=dict)
    # Authentication state
    auth_state: str = "ANONYMOUS"
    # Last-known values for diagnostics
    last_user_intent: str | None = None
    last_action: str | None = None
    last_component: str | None = None
    last_successful_page: str | None = "/"
    last_failed_navigation: str | None = None
    navigation_errors: list[str] = field(default_factory=list)
    last_api_call: str | None = None
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Return a defensive copy of the session state as a plain dict."""
        return {
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "current_page": self.current_page,
            "previous_page": self.previous_page,
            "current_component": self.current_component,
            "current_section": self.current_section,
            "current_modal": self.current_modal,
            "current_tab": self.current_tab,
            "focused_input": self.focused_input,
            "scroll_position": self.scroll_position,
            "selected_card": self.selected_card,
            "selected_table_row": self.selected_table_row,
            "current_route_parameters": dict(self.current_route_parameters),
            "pending_navigation": self.pending_navigation,
            "pending_action": self.pending_action,
            "active_workflow": self.active_workflow,
            "workflow_step": self.workflow_step,
            "navigation_history": list(self.navigation_history),
            "visited_pages": list(self.visited_pages),
            "navigation_frequency": dict(self.navigation_frequency),
            "breadcrumb_trail": list(self.breadcrumb_trail),
            "undo_stack": list(self.undo_stack),
            "redo_stack": list(self.redo_stack),
            "favorite_routes": list(self.favorite_routes),
            "workflow_checkpoints": dict(self.workflow_checkpoints),
            "auth_state": self.auth_state,
            "last_user_intent": self.last_user_intent,
            "last_action": self.last_action,
            "last_component": self.last_component,
            "last_successful_page": self.last_successful_page,
            "last_failed_navigation": self.last_failed_navigation,
            "navigation_errors": list(self.navigation_errors),
            "last_api_call": self.last_api_call,
            "updated_at": self.updated_at,
        }


class NavigationStateStore:
    """Thread-safe session navigation state store.

    Owns ONLY runtime session state:
      - current page, previous page, UI focus, scroll position
      - navigation history, undo/redo stacks
      - workflow runtime position (no step logic)
      - navigation errors and diagnostics

    Does NOT own:
      - conversation history (→ ConversationMemoryManager)
      - extracted entities or slots (→ ConversationMemoryManager)
      - static route metadata (→ RouteRegistry)
    """

    def __init__(self) -> None:
        self._sessions: dict[str, NavigationSessionState] = {}
        self._lock = RLock()
        self._update_count = 0
        self._started_at = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_or_create(self, session_id: str) -> NavigationSessionState:
        """Get or initialize a session state (must be called under lock)."""
        if session_id not in self._sessions:
            self._sessions[session_id] = NavigationSessionState(session_id=session_id)
        return self._sessions[session_id]

    @staticmethod
    def _prune_history(history: list[str]) -> None:
        """Prune navigation history to _MAX_NAVIGATION_HISTORY entries (oldest first)."""
        while len(history) > _MAX_NAVIGATION_HISTORY:
            history.pop(0)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_state(self, session_id: str) -> NavigationSessionState:
        """Get or initialize navigation session state. Complexity: O(1)."""
        with self._lock:
            return self._get_or_create(session_id)

    def update_current_page(
        self,
        session_id: str,
        page_path: str,
        parameters: dict[str, Any] | None = None,
    ) -> NavigationSessionState:
        """Navigate session to a new page path.

        Updates history, visited pages, frequency map, undo stack. Resets redo stack.
        Navigation history is bounded to MAX_NAVIGATION_HISTORY entries.
        """
        with self._lock:
            state = self._get_or_create(session_id)

            if state.current_page != page_path:
                state.undo_stack.append(state.current_page)
                state.previous_page = state.current_page
                state.current_page = page_path
                state.last_successful_page = page_path
                state.navigation_history.append(page_path)
                self._prune_history(state.navigation_history)
                state.redo_stack.clear()

            state.visited_pages.add(page_path)
            state.navigation_frequency[page_path] = state.navigation_frequency.get(page_path, 0) + 1

            if parameters:
                state.current_route_parameters.update(parameters)

            self._update_count += 1
            state.updated_at = datetime.now(timezone.utc).isoformat()
            logger.debug(
                "Session navigated [operation=update_current_page, session_id=%s, route=%s, visited_count=%d]",
                session_id,
                page_path,
                len(state.visited_pages),
            )
            return state

    def update_ui_state(
        self,
        session_id: str,
        component: str | None = None,
        section: str | None = None,
        modal: str | None = None,
        tab: str | None = None,
        focused_input: str | None = None,
        scroll_position: int | None = None,
        selected_card: str | None = None,
        selected_table_row: str | None = None,
    ) -> NavigationSessionState:
        """Update UI component interaction state for a session."""
        with self._lock:
            state = self._get_or_create(session_id)
            if component is not None:
                state.current_component = component
                state.last_component = component
            if section is not None:
                state.current_section = section
            if modal is not None:
                state.current_modal = modal
            if tab is not None:
                state.current_tab = tab
            if focused_input is not None:
                state.focused_input = focused_input
            if scroll_position is not None:
                state.scroll_position = scroll_position
            if selected_card is not None:
                state.selected_card = selected_card
            if selected_table_row is not None:
                state.selected_table_row = selected_table_row

            self._update_count += 1
            state.updated_at = datetime.now(timezone.utc).isoformat()
            return state

    def update_workflow(
        self,
        session_id: str,
        workflow_name: str | None,
        step_name: str | None = None,
    ) -> NavigationSessionState:
        """Update active workflow runtime position and checkpoint map."""
        with self._lock:
            state = self._get_or_create(session_id)
            state.active_workflow = workflow_name
            state.workflow_step = step_name
            if workflow_name and step_name:
                state.workflow_checkpoints[workflow_name] = step_name
            self._update_count += 1
            state.updated_at = datetime.now(timezone.utc).isoformat()
            return state

    def set_pending_navigation(
        self,
        session_id: str,
        target_route: str | None,
        action: str | None = None,
    ) -> None:
        """Set pending navigation target route and action directive."""
        with self._lock:
            state = self._get_or_create(session_id)
            state.pending_navigation = target_route
            state.pending_action = action
            if action:
                state.last_action = action
            self._update_count += 1
            state.updated_at = datetime.now(timezone.utc).isoformat()

    def record_error(self, session_id: str, failed_route: str, error_message: str) -> None:
        """Record a navigation failure for session diagnostics."""
        with self._lock:
            state = self._get_or_create(session_id)
            state.last_failed_navigation = failed_route
            state.navigation_errors.append(f"{failed_route}: {error_message}")
            state.updated_at = datetime.now(timezone.utc).isoformat()
            logger.warning(
                "Navigation error recorded [operation=record_error, session_id=%s, route=%s, reason=%s]",
                session_id,
                failed_route,
                error_message,
            )

    def undo(self, session_id: str) -> str | None:
        """Pop the undo stack and navigate back one step.

        Returns:
            The previous page path, or None if the undo stack is empty.
        """
        with self._lock:
            state = self._get_or_create(session_id)
            if not state.undo_stack:
                return None
            prev = state.undo_stack.pop()
            state.redo_stack.append(state.current_page)
            state.previous_page = state.current_page
            state.current_page = prev
            state.navigation_history.append(prev)
            self._prune_history(state.navigation_history)
            self._update_count += 1
            state.updated_at = datetime.now(timezone.utc).isoformat()
            logger.debug(
                "Undo navigation [operation=undo, session_id=%s, reverted_to=%s]",
                session_id,
                prev,
            )
            return prev

    def clear_session(self, session_id: str) -> None:
        """Remove a session from the store."""
        with self._lock:
            self._sessions.pop(session_id, None)

    def statistics(self) -> dict[str, Any]:
        """Return read-only enterprise diagnostics for NavigationStateStore."""
        with self._lock:
            histories = [len(s.navigation_history) for s in self._sessions.values()]
            avg_history = round(sum(histories) / len(histories), 2) if histories else 0.0
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "active_sessions_count": len(self._sessions),
                "total_update_count": self._update_count,
                "average_history_length": avg_history,
                "max_history_limit": _MAX_NAVIGATION_HISTORY,
                "sessions": [s.session_id for s in self._sessions.values()],
            }

    def health(self) -> dict[str, Any]:
        """Return read-only health status for NavigationStateStore."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "status": "HEALTHY",
                "active_sessions": len(self._sessions),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
