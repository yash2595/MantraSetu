"""Strongly typed immutable domain models and enums for Navigation Planning Layer in MantraSetu AgentOS."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


def _utc_now_iso() -> str:
    """Return ISO 8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


class PlanningStrategy(StrEnum):
    """Enumeration of navigation planning strategies."""

    SHORTEST_PATH = "SHORTEST_PATH"
    WORKFLOW_PATH = "WORKFLOW_PATH"
    RESUME_PATH = "RESUME_PATH"
    RECOVERY_PATH = "RECOVERY_PATH"
    AUTHENTICATION_PATH = "AUTHENTICATION_PATH"
    ALTERNATE_PATH = "ALTERNATE_PATH"
    ROLLBACK_PATH = "ROLLBACK_PATH"
    BACKTRACKING_PATH = "BACKTRACKING_PATH"


@dataclass(frozen=True)
class NavigationStep:
    """Immutable representation of an individual step in a navigation plan."""

    step_id: str
    step_index: int
    source_route: str
    target_route: str
    action_type: str = "NAVIGATE"
    description: str = ""
    required_parameters: dict[str, Any] = field(default_factory=dict)
    is_mandatory: bool = True
    estimated_latency_ms: float = 10.0


@dataclass(frozen=True)
class NavigationPath:
    """Immutable graph path computation result."""

    path_nodes: tuple[str, ...]
    path_edges: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    total_cost: float = 0.0
    total_steps: int = 0
    planning_strategy: PlanningStrategy = PlanningStrategy.SHORTEST_PATH
    confidence: float = 1.0
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NavigationPlan:
    """Immutable executable multi-step navigation plan."""

    plan_id: str
    goal: str
    strategy: PlanningStrategy
    target_route: str
    steps: tuple[NavigationStep, ...]
    path: NavigationPath
    confidence: float = 1.0
    estimated_cost: float = 0.0
    estimated_latency_ms: float = 0.0
    diagnostics: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        """Serialize navigation plan to dictionary."""
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "strategy": self.strategy.value,
            "target_route": self.target_route,
            "steps": [
                {
                    "step_id": s.step_id,
                    "step_index": s.step_index,
                    "source_route": s.source_route,
                    "target_route": s.target_route,
                    "action_type": s.action_type,
                    "description": s.description,
                    "required_parameters": dict(s.required_parameters),
                    "is_mandatory": s.is_mandatory,
                    "estimated_latency_ms": s.estimated_latency_ms,
                }
                for s in self.steps
            ],
            "path": {
                "nodes": list(self.path.path_nodes),
                "edges": list(self.path.path_edges),
                "total_cost": self.path.total_cost,
                "total_steps": self.path.total_steps,
                "planning_strategy": self.path.planning_strategy.value,
                "confidence": self.path.confidence,
            },
            "confidence": self.confidence,
            "estimated_cost": self.estimated_cost,
            "estimated_latency_ms": self.estimated_latency_ms,
            "diagnostics": dict(self.diagnostics),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class RecoveryPlan:
    """Immutable recovery plan for interrupted or failed navigation journeys."""

    recovery_id: str
    reason: str
    recovery_steps: tuple[NavigationStep, ...]
    retry_count: int = 1
    target_checkpoint: str | None = None
    estimated_cost: float = 0.0
    diagnostics: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now_iso)


@dataclass(frozen=True)
class AlternateNavigationPlan:
    """Immutable fallback route plan when primary target path is blocked or unavailable."""

    alternate_id: str
    primary_target: str
    alternate_target: str
    strategy: PlanningStrategy
    steps: tuple[NavigationStep, ...]
    confidence: float = 0.85
    reason: str = ""
    diagnostics: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now_iso)


@dataclass(frozen=True)
class PlanningResult:
    """Unified planning execution result."""

    result_id: str
    success: bool
    plan: NavigationPlan | None = None
    recovery_plan: RecoveryPlan | None = None
    alternate_plan: AlternateNavigationPlan | None = None
    strategy: PlanningStrategy = PlanningStrategy.SHORTEST_PATH
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlanningDiagnostics:
    """Diagnostic snapshot for planning component audit and observability."""

    component_name: str
    component_version: str
    started_at: str
    uptime_seconds: float
    timestamp: str
    plans_generated: int
    shortest_paths_generated: int
    alternate_paths_generated: int
    recovery_plans_generated: int
    rollback_plans_generated: int
    average_path_length: float
    average_planning_latency_ms: float
    graph_traversals: int
    cache_hits: int
    cache_misses: int
    thread_safe: bool = True
    memory_usage_estimate: str = "1.0 MB"


@dataclass(frozen=True)
class PlanningMetadata:
    """Container for planning context metadata."""

    session_id: str = ""
    conversation_id: str = ""
    trace_id: str = field(default_factory=lambda: f"tr_{uuid4().hex[:8]}")
    request_id: str = field(default_factory=lambda: f"req_{uuid4().hex[:8]}")
    decision_id: str = ""
    metadata_version: str = "4.1"
