"""Chronological History Timeline & Safe Read-Only Session Replay Engine for Navigation Journey v4.1."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.journey_models import (
    NavigationTransition,
    ReplayMode,
    TransitionStatus,
)

logger = logging.getLogger(__name__)


class NavigationHistoryTimeline:
    """Chronological history manager for session screen transitions with safe READ_ONLY session replay."""

    def __init__(self, max_size: int = 200) -> None:
        self._max_size = max_size
        self._transitions: list[NavigationTransition] = []
        self._undo_stack: list[str] = []
        self._redo_stack: list[str] = []
        self._lock = RLock()
        self._replay_count = 0

    def add_transition(self, transition: NavigationTransition) -> None:
        """Append transition to timeline and update undo/redo stacks."""
        with self._lock:
            self._transitions.append(transition)
            if len(self._transitions) > self._max_size:
                self._transitions.pop(0)

            curr = transition.current_page or transition.target_page
            prev = transition.previous_page

            if prev and (not self._undo_stack or self._undo_stack[-1] != prev):
                self._undo_stack.append(prev)
            if curr:
                self._undo_stack.append(curr)

            # Clear redo stack on new forward transition
            self._redo_stack.clear()

    def undo(self) -> str | None:
        """Simulate browser back navigation in timeline."""
        with self._lock:
            if len(self._undo_stack) <= 1:
                return None
            current = self._undo_stack.pop()
            self._redo_stack.append(current)
            return self._undo_stack[-1]

    def redo(self) -> str | None:
        """Simulate browser forward navigation in timeline."""
        with self._lock:
            if not self._redo_stack:
                return None
            target = self._redo_stack.pop()
            self._undo_stack.append(target)
            return target

    def replay(
        self,
        mode: ReplayMode = ReplayMode.FULL_REPLAY,
        workflow_id: str | None = None,
        page_filter: str | None = None,
        status_filter: TransitionStatus | None = None,
    ) -> list[NavigationTransition]:
        """Execute READ_ONLY replay reconstruction of session timeline.

        CRITICAL: Replay executes strictly in READ_ONLY mode and NEVER mutates
        NavigationStateStore, ConversationMemoryManager, WorkflowTracker, or JourneyStore.
        """
        with self._lock:
            self._replay_count += 1
            result: list[NavigationTransition] = []

            for t in self._transitions:
                # Mode filtering
                if mode == ReplayMode.WORKFLOW_ONLY:
                    if not t.workflow_id or (workflow_id and t.workflow_id != workflow_id):
                        continue
                elif mode == ReplayMode.FAILED_TRANSITIONS_ONLY:
                    if t.transition_status == TransitionStatus.SUCCESS:
                        continue
                elif mode == ReplayMode.USER_ACTIONS_ONLY:
                    if t.triggering_ai_intent is not None:
                        continue
                elif mode == ReplayMode.AI_DECISIONS_ONLY:
                    if t.triggering_ai_intent is None:
                        continue

                # Additional optional filters
                if page_filter and page_filter not in (t.current_page, t.previous_page, t.target_page):
                    continue
                if status_filter and t.transition_status != status_filter:
                    continue

                result.append(t)

            logger.debug("Executed READ_ONLY timeline replay [Mode: %s, Returned: %d/%d]", mode, len(result), len(self._transitions))
            return list(result)

    def get_backtracking_count(self) -> int:
        """Count number of backward/undo navigations in timeline."""
        with self._lock:
            count = 0
            for i in range(1, len(self._transitions)):
                t_curr = self._transitions[i]
                t_prev = self._transitions[i - 1]
                if t_curr.current_page == t_prev.previous_page:
                    count += 1
            return count

    def get_last_successful_transition(self) -> NavigationTransition | None:
        """Retrieve last successful transition from timeline."""
        with self._lock:
            for t in reversed(self._transitions):
                if t.transition_status == TransitionStatus.SUCCESS:
                    return t
            return None

    def get_last_failed_transition(self) -> NavigationTransition | None:
        """Retrieve last failed transition from timeline."""
        with self._lock:
            for t in reversed(self._transitions):
                if t.transition_status == TransitionStatus.FAILED:
                    return t
            return None

    def get_all_transitions(self) -> list[NavigationTransition]:
        """Return defensive snapshot list of all recorded transitions."""
        with self._lock:
            return list(self._transitions)

    # Diagnostics & Health
    def statistics(self) -> dict[str, Any]:
        """Expose timeline operational statistics."""
        with self._lock:
            return {
                "total_transitions_recorded": len(self._transitions),
                "undo_stack_depth": len(self._undo_stack),
                "redo_stack_depth": len(self._redo_stack),
                "backtracking_count": self.get_backtracking_count(),
                "replay_count": self._replay_count,
            }

    def health(self) -> ComponentHealth:
        """Expose timeline health status."""
        return ComponentHealth(
            component_name="NavigationHistoryTimeline",
            status=SystemHealthStatus.HEALTHY,
            details=self.statistics(),
        )

    def metrics(self) -> dict[str, Any]:
        """Expose operational metrics."""
        return self.statistics()
