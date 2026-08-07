"""Versioned Weighted Directed Transition Graph for Enterprise Navigation Journey Intelligence v4.1."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.journey_models import NavigationTransition, PredictedRoute, TransitionStatus

logger = logging.getLogger(__name__)

_GRAPH_VERSION = "4.1.0"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class JourneyEdge:
    """Weighted edge representing transitions between two pages."""

    source_page: str
    target_page: str
    transition_count: int = 0
    total_latency_ms: float = 0.0
    average_latency_ms: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 1.0
    failure_rate: float = 0.0
    workflow_frequency: dict[str, int] = field(default_factory=dict)
    ai_generated_transition: bool = False
    last_used_timestamp: str = field(default_factory=_utc_now_iso)
    validation_status: str = "VALIDATED"
    transition_reason: str = "NAVIGATION"

    def record_transition(self, transition: NavigationTransition) -> None:
        """Update weighted edge state with new transition observation."""
        self.transition_count += 1
        self.total_latency_ms += transition.transition_duration
        self.average_latency_ms = self.total_latency_ms / self.transition_count

        if transition.transition_status == TransitionStatus.SUCCESS:
            self.success_count += 1
        else:
            self.failure_count += 1

        total = self.success_count + self.failure_count
        self.success_rate = (self.success_count / total) if total > 0 else 1.0
        self.failure_rate = (self.failure_count / total) if total > 0 else 0.0

        if transition.workflow_id:
            self.workflow_frequency[transition.workflow_id] = self.workflow_frequency.get(transition.workflow_id, 0) + 1

        if transition.triggering_ai_intent:
            self.ai_generated_transition = True

        self.last_used_timestamp = transition.timestamp
        self.transition_reason = transition.navigation_action

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_page": self.source_page,
            "target_page": self.target_page,
            "transition_count": self.transition_count,
            "total_latency_ms": self.total_latency_ms,
            "average_latency_ms": self.average_latency_ms,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_rate,
            "failure_rate": self.failure_rate,
            "workflow_frequency": dict(self.workflow_frequency),
            "ai_generated_transition": self.ai_generated_transition,
            "last_used_timestamp": self.last_used_timestamp,
            "validation_status": self.validation_status,
            "transition_reason": self.transition_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JourneyEdge:
        return cls(
            source_page=data.get("source_page", "/"),
            target_page=data.get("target_page", "/"),
            transition_count=int(data.get("transition_count", 0)),
            total_latency_ms=float(data.get("total_latency_ms", 0.0)),
            average_latency_ms=float(data.get("average_latency_ms", 0.0)),
            success_count=int(data.get("success_count", 0)),
            failure_count=int(data.get("failure_count", 0)),
            success_rate=float(data.get("success_rate", 1.0)),
            failure_rate=float(data.get("failure_rate", 0.0)),
            workflow_frequency=dict(data.get("workflow_frequency") or {}),
            ai_generated_transition=bool(data.get("ai_generated_transition", False)),
            last_used_timestamp=data.get("last_used_timestamp", _utc_now_iso()),
            validation_status=data.get("validation_status", "VALIDATED"),
            transition_reason=data.get("transition_reason", "NAVIGATION"),
        )


class NavigationJourneyGraph:
    """Thread-safe versioned weighted directed graph representing user screen transitions."""

    def __init__(self, version: str = _GRAPH_VERSION) -> None:
        self.graph_version = version
        self.created_at = _utc_now_iso()
        self.updated_at = _utc_now_iso()
        # Adjacency list: source_page -> {target_page -> JourneyEdge}
        self._outgoing_edges: dict[str, dict[str, JourneyEdge]] = {}
        # Reverse adjacency list: target_page -> {source_page -> JourneyEdge}
        self._incoming_edges: dict[str, dict[str, JourneyEdge]] = {}
        self._lock = RLock()
        self._prediction_count = 0

    def add_transition(self, transition: NavigationTransition) -> JourneyEdge:
        """Record transition into graph, creating or updating weighted directed edge."""
        with self._lock:
            src = transition.previous_page or "/"
            tgt = transition.current_page or transition.target_page or "/"

            if src not in self._outgoing_edges:
                self._outgoing_edges[src] = {}
            if tgt not in self._incoming_edges:
                self._incoming_edges[tgt] = {}

            edge = self._outgoing_edges[src].get(tgt)
            if edge is None:
                edge = JourneyEdge(source_page=src, target_page=tgt)
                self._outgoing_edges[src][tgt] = edge
                self._incoming_edges[tgt][src] = edge

            edge.record_transition(transition)
            self.updated_at = _utc_now_iso()
            return edge

    def get_probable_next_destinations(self, current_page: str, limit: int = 5) -> list[PredictedRoute]:
        """Predict likely next destinations from current page based on transition frequency and success rate."""
        with self._lock:
            self._prediction_count += 1
            outgoing = self._outgoing_edges.get(current_page, {})
            if not outgoing:
                return []

            total_weight = sum(e.transition_count for e in outgoing.values())
            if total_weight == 0:
                return []

            results: list[PredictedRoute] = []
            for tgt, edge in outgoing.items():
                conf = (edge.transition_count / total_weight) * edge.success_rate
                results.append(
                    PredictedRoute(
                        route=tgt,
                        confidence=round(min(max(conf, 0.0), 1.0), 4),
                        reason=f"Historical transitions: {edge.transition_count}, success rate: {int(edge.success_rate * 100)}%",
                        confidence_source="WEIGHTED_JOURNEY_GRAPH",
                    )
                )

            results.sort(key=lambda r: r.confidence, reverse=True)
            return results[:limit]

    def get_probable_previous_pages(self, current_page: str, limit: int = 5) -> list[PredictedRoute]:
        """Predict likely previous origin pages from current page."""
        with self._lock:
            self._prediction_count += 1
            incoming = self._incoming_edges.get(current_page, {})
            if not incoming:
                return []

            total_weight = sum(e.transition_count for e in incoming.values())
            if total_weight == 0:
                return []

            results: list[PredictedRoute] = []
            for src, edge in incoming.items():
                conf = (edge.transition_count / total_weight) * edge.success_rate
                results.append(
                    PredictedRoute(
                        route=src,
                        confidence=round(min(max(conf, 0.0), 1.0), 4),
                        reason=f"Historical incoming transitions: {edge.transition_count}",
                        confidence_source="WEIGHTED_JOURNEY_GRAPH",
                    )
                )

            results.sort(key=lambda r: r.confidence, reverse=True)
            return results[:limit]

    def predict_resume_destination(self, workflow_id: str) -> PredictedRoute | None:
        """Predict most probable resume destination for a given workflow ID."""
        with self._lock:
            self._prediction_count += 1
            best_edge: JourneyEdge | None = None
            best_count = -1

            for src, targets in self._outgoing_edges.items():
                for tgt, edge in targets.items():
                    wf_cnt = edge.workflow_frequency.get(workflow_id, 0)
                    if wf_cnt > best_count:
                        best_count = wf_cnt
                        best_edge = edge

            if not best_edge or best_count <= 0:
                return None

            return PredictedRoute(
                route=best_edge.target_page,
                confidence=0.9,
                reason=f"Active workflow checkpoint target for workflow '{workflow_id}'",
                confidence_source="WORKFLOW_RESUME_PREDICTOR",
            )

    def predict_workflow_completion(self, workflow_id: str, current_step: str) -> float:
        """Predict workflow completion percentage based on graph step density."""
        with self._lock:
            self._prediction_count += 1
            # Step density heuristic
            wf_edges = [
                e for src in self._outgoing_edges.values()
                for e in src.values()
                if workflow_id in e.workflow_frequency
            ]
            if not wf_edges:
                return 0.5
            avg_success = sum(e.success_rate for e in wf_edges) / len(wf_edges)
            return round(avg_success, 4)

    def detect_navigation_loops(self, session_id: str = "") -> list[list[str]]:
        """Detect circular loops (e.g. A -> B -> A) in transition graph."""
        with self._lock:
            loops: list[list[str]] = []
            for src, targets in self._outgoing_edges.items():
                for tgt in targets.keys():
                    if src != tgt and tgt in self._outgoing_edges and src in self._outgoing_edges[tgt]:
                        pair = sorted([src, tgt])
                        if pair not in loops:
                            loops.append(pair)
            return loops

    def detect_dead_end_routes(self) -> list[str]:
        """Detect pages with incoming transitions but no outgoing transitions."""
        with self._lock:
            dead_ends: list[str] = []
            all_pages = set(self._outgoing_edges.keys()).union(self._incoming_edges.keys())
            for page in all_pages:
                outgoing = self._outgoing_edges.get(page, {})
                incoming = self._incoming_edges.get(page, {})
                if incoming and not outgoing:
                    dead_ends.append(page)
            return dead_ends

    def to_dict(self) -> dict[str, Any]:
        """Serialize graph to dictionary representation."""
        with self._lock:
            edges_list = []
            for src, targets in self._outgoing_edges.items():
                for tgt, edge in targets.items():
                    edges_list.append(edge.to_dict())

            return {
                "graph_version": self.graph_version,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
                "edges": edges_list,
            }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NavigationJourneyGraph:
        """Deserialize graph from dictionary representation."""
        graph = cls(version=data.get("graph_version", _GRAPH_VERSION))
        graph.created_at = data.get("created_at", _utc_now_iso())
        graph.updated_at = data.get("updated_at", _utc_now_iso())

        for edge_dict in data.get("edges", []):
            edge = JourneyEdge.from_dict(edge_dict)
            src = edge.source_page
            tgt = edge.target_page
            if src not in graph._outgoing_edges:
                graph._outgoing_edges[src] = {}
            if tgt not in graph._incoming_edges:
                graph._incoming_edges[tgt] = {}
            graph._outgoing_edges[src][tgt] = edge
            graph._incoming_edges[tgt][src] = edge

        return graph

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> NavigationJourneyGraph:
        return cls.from_dict(json.loads(json_str))

    # Diagnostics & Health
    def statistics(self) -> dict[str, Any]:
        """Expose graph operational statistics."""
        with self._lock:
            edge_count = sum(len(targets) for targets in self._outgoing_edges.values())
            node_count = len(set(self._outgoing_edges.keys()).union(self._incoming_edges.keys()))
            return {
                "graph_version": self.graph_version,
                "node_count": node_count,
                "edge_count": edge_count,
                "prediction_count": self.prediction_count,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
            }

    @property
    def prediction_count(self) -> int:
        return self._prediction_count

    def health(self) -> ComponentHealth:
        """Expose graph health status."""
        return ComponentHealth(
            component_name="NavigationJourneyGraph",
            status=SystemHealthStatus.HEALTHY,
            details=self.statistics(),
        )

    def metrics(self) -> dict[str, Any]:
        """Expose operational metrics."""
        return self.statistics()
