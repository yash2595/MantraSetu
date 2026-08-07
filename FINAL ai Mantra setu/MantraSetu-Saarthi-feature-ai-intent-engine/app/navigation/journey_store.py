"""Enterprise Thread-Safe Navigation Journey Lifecycle Store for MantraSetu AgentOS v4.1."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.journey_graph import NavigationJourneyGraph
from app.navigation.journey_models import (
    JourneyCheckpoint,
    NavigationJourney,
    NavigationTransition,
)
from app.navigation.journey_persistence import (
    InMemoryProvider,
    JourneyPersistenceProvider,
)
from app.navigation.journey_timeline import NavigationHistoryTimeline

logger = logging.getLogger(__name__)

_DEFAULT_MAX_TRANSITION_COUNT = 500
_DEFAULT_CLEANUP_INTERVAL_SECONDS = 3600


class NavigationJourneyStore:
    """Thread-safe enterprise store managing per-session NavigationJourney, NavigationJourneyGraph, and NavigationHistoryTimeline."""

    def __init__(
        self,
        persistence_provider: JourneyPersistenceProvider | None = None,
        max_transition_count: int = _DEFAULT_MAX_TRANSITION_COUNT,
        automatic_pruning: bool = True,
        cleanup_interval_seconds: int = _DEFAULT_CLEANUP_INTERVAL_SECONDS,
    ) -> None:
        self._provider = persistence_provider or InMemoryProvider()
        self._max_transition_count = max_transition_count
        self._automatic_pruning = automatic_pruning
        self._cleanup_interval_seconds = cleanup_interval_seconds
        self._last_cleanup_timestamp = time.time()

        # Graphs per session
        self._graphs: dict[str, NavigationJourneyGraph] = {}
        # Timelines per session
        self._timelines: dict[str, NavigationHistoryTimeline] = {}
        self._lock = RLock()

        # Metrics counters
        self._total_transitions_recorded = 0
        self._export_count = 0
        self._import_count = 0

    def record_transition(self, transition: NavigationTransition) -> NavigationJourney:
        """Record transition into session journey, transition graph, and history timeline."""
        with self._lock:
            sid = transition.session_id
            if not sid:
                raise ValueError("NavigationTransition must contain a valid session_id.")

            journey = self.get_journey(sid)
            journey.transitions.append(transition)

            # Enforce max transition count via automatic pruning if enabled
            if self._automatic_pruning and len(journey.transitions) > self._max_transition_count:
                journey.transitions = journey.transitions[-self._max_transition_count:]

            journey.updated_at = datetime.now(timezone.utc).isoformat()
            if transition.workflow_id:
                journey.active_workflow = transition.workflow_id
            if transition.workflow_step:
                journey.workflow_step = transition.workflow_step

            # Update Graph & Timeline
            graph = self.get_graph(sid)
            graph.add_transition(transition)

            timeline = self.get_timeline(sid)
            timeline.add_transition(transition)

            self._provider.save_journey(journey)
            self._total_transitions_recorded += 1
            return journey

    def get_journey(self, session_id: str) -> NavigationJourney:
        """Retrieve existing journey or initialize a new one for session_id."""
        with self._lock:
            journey = self._provider.load_journey(session_id)
            if journey is None:
                journey = NavigationJourney(session_id=session_id)
                self._provider.save_journey(journey)
            return journey

    def get_graph(self, session_id: str) -> NavigationJourneyGraph:
        """Retrieve or create session weighted transition graph."""
        with self._lock:
            if session_id not in self._graphs:
                graph = NavigationJourneyGraph()
                # Populate existing graph state if journey transitions exist
                journey = self._provider.load_journey(session_id)
                if journey:
                    for t in journey.transitions:
                        graph.add_transition(t)
                self._graphs[session_id] = graph
            return self._graphs[session_id]

    def get_timeline(self, session_id: str) -> NavigationHistoryTimeline:
        """Retrieve or create session history timeline."""
        with self._lock:
            if session_id not in self._timelines:
                timeline = NavigationHistoryTimeline(max_size=self._max_transition_count)
                journey = self._provider.load_journey(session_id)
                if journey:
                    for t in journey.transitions:
                        timeline.add_transition(t)
                self._timelines[session_id] = timeline
            return self._timelines[session_id]

    def set_checkpoint(self, session_id: str, checkpoint: JourneyCheckpoint) -> None:
        """Save a resume checkpoint for session's active workflow."""
        with self._lock:
            journey = self.get_journey(session_id)
            journey.resume_checkpoint = checkpoint
            journey.updated_at = datetime.now(timezone.utc).isoformat()
            self._provider.save_journey(journey)

    def get_checkpoint(self, session_id: str) -> JourneyCheckpoint | None:
        """Retrieve active resume checkpoint for session."""
        with self._lock:
            journey = self.get_journey(session_id)
            return journey.resume_checkpoint

    def clear_checkpoint(self, session_id: str) -> None:
        """Clear active resume checkpoint for session."""
        with self._lock:
            journey = self.get_journey(session_id)
            journey.resume_checkpoint = None
            journey.updated_at = datetime.now(timezone.utc).isoformat()
            self._provider.save_journey(journey)

    # Enterprise Lifecycle Operations
    def export_session(self, session_id: str) -> dict[str, Any]:
        """Export session journey, graph, and timeline data as a serializable dict."""
        with self._lock:
            self._export_count += 1
            journey = self.get_journey(session_id)
            graph = self.get_graph(session_id)
            timeline = self.get_timeline(session_id)
            return {
                "journey": journey.to_dict(),
                "graph": graph.to_dict(),
                "timeline_stats": timeline.statistics(),
            }

    def import_session(self, session_data: dict[str, Any]) -> NavigationJourney:
        """Import and register session journey and graph state from serialized dictionary."""
        with self._lock:
            self._import_count += 1
            journey_dict = session_data.get("journey", session_data)
            journey = NavigationJourney.from_dict(journey_dict)
            self._provider.save_journey(journey)

            if "graph" in session_data:
                graph = NavigationJourneyGraph.from_dict(session_data["graph"])
                self._graphs[journey.session_id] = graph

            return journey

    def archive_session(self, session_id: str) -> bool:
        """Archive an active session journey."""
        with self._lock:
            journey = self._provider.load_journey(session_id)
            if journey:
                journey.is_archived = True
                journey.updated_at = datetime.now(timezone.utc).isoformat()
                self._provider.save_journey(journey)
                return True
            return False

    def cleanup_expired_sessions(self, max_age_seconds: int = 86400) -> int:
        """Remove sessions older than max_age_seconds."""
        with self._lock:
            now = datetime.now(timezone.utc).timestamp()
            removed_count = 0
            for sid in self._provider.list_all_sessions():
                j = self._provider.load_journey(sid)
                if j and j.updated_at:
                    try:
                        updated_ts = datetime.fromisoformat(j.updated_at).timestamp()
                        if (now - updated_ts) > max_age_seconds:
                            self._provider.delete_journey(sid)
                            self._graphs.pop(sid, None)
                            self._timelines.pop(sid, None)
                            removed_count += 1
                    except Exception:
                        pass
            return removed_count

    def clear_completed_sessions(self) -> int:
        """Remove archived or completed sessions."""
        with self._lock:
            removed_count = 0
            for sid in self._provider.list_all_sessions():
                j = self._provider.load_journey(sid)
                if j and (j.is_archived or (j.resume_checkpoint is None and not j.active_workflow)):
                    self._provider.delete_journey(sid)
                    self._graphs.pop(sid, None)
                    self._timelines.pop(sid, None)
                    removed_count += 1
            return removed_count

    # Diagnostics & Health
    def statistics(self) -> dict[str, Any]:
        """Expose journey store operational statistics."""
        with self._lock:
            all_sessions = self._provider.list_all_sessions()
            active_sessions = self._provider.list_active_sessions()
            return {
                "total_sessions": len(all_sessions),
                "active_sessions": len(active_sessions),
                "total_transitions_recorded": self._total_transitions_recorded,
                "cached_graphs": len(self._graphs),
                "cached_timelines": len(self._timelines),
                "export_count": self._export_count,
                "import_count": self._import_count,
            }

    def health(self) -> ComponentHealth:
        """Expose journey store health status."""
        return ComponentHealth(
            component_name="NavigationJourneyStore",
            status=SystemHealthStatus.HEALTHY,
            details=self.statistics(),
        )

    def metrics(self) -> dict[str, Any]:
        """Expose operational metrics."""
        return self.statistics()
