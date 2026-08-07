"""Pipeline Stage Registry for Enterprise AgentOS Pipeline v1.1."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Dict, List, Optional


@dataclass
class StageMetadata:
    """Metadata tracking a pipeline stage."""

    name: str
    execution_order: int
    dependencies: List[str] = field(default_factory=list)
    enabled: bool = True
    average_latency_ms: float = 0.0
    execution_count: int = 0
    health_state: str = "HEALTHY"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "execution_order": self.execution_order,
            "dependencies": list(self.dependencies),
            "enabled": self.enabled,
            "average_latency_ms": round(self.average_latency_ms, 3),
            "execution_count": self.execution_count,
            "health_state": self.health_state,
        }


DEFAULT_PIPELINE_STAGES = [
    ("Voice Gateway", 1, []),
    ("STT Manager", 2, ["Voice Gateway"]),
    ("Conversation Manager", 3, ["STT Manager"]),
    ("Intent Engine", 4, ["Conversation Manager"]),
    ("Entity Extractor", 5, ["Intent Engine"]),
    ("Slot Manager", 6, ["Entity Extractor"]),
    ("Conversation Context Builder", 7, ["Slot Manager"]),
    ("Memory Manager (Recall)", 8, ["Conversation Context Builder"]),
    ("Knowledge Framework (RAG)", 9, ["Memory Manager (Recall)"]),
    ("Prompt Builder", 10, ["Knowledge Framework (RAG)"]),
    ("LLM Provider", 11, ["Prompt Builder"]),
    ("Prediction Engine", 12, ["LLM Provider"]),
    ("Tool Selector", 13, ["Prediction Engine"]),
    ("Tool Validator", 14, ["Tool Selector"]),
    ("Tool Executor", 15, ["Tool Validator"]),
    ("Navigation Decision Engine", 16, ["Tool Executor"]),
    ("Navigation Journey Store", 17, ["Navigation Decision Engine"]),
    ("Voice Form Controller", 18, ["Navigation Journey Store"]),
    ("Frontend Sync Manager", 19, ["Voice Form Controller"]),
    ("Response Builder", 20, ["Frontend Sync Manager"]),
    ("TTS Manager", 21, ["Response Builder"]),
    ("Memory Store & Telemetry", 22, ["TTS Manager"]),
]


class PipelineStageRegistry:
    """Internal registry maintaining metadata and execution statistics for all 22 pipeline stages."""

    def __init__(self):
        self._lock = RLock()
        self._stages: Dict[str, StageMetadata] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        for name, order, deps in DEFAULT_PIPELINE_STAGES:
            self._stages[name] = StageMetadata(name=name, execution_order=order, dependencies=deps)

    def register_stage(self, name: str, execution_order: int, dependencies: Optional[List[str]] = None) -> StageMetadata:
        """Register or update a stage definition."""
        with self._lock:
            meta = StageMetadata(name=name, execution_order=execution_order, dependencies=dependencies or [])
            self._stages[name] = meta
            return meta

    def get_stage(self, name: str) -> Optional[StageMetadata]:
        """Get metadata for a stage."""
        with self._lock:
            return self._stages.get(name)

    def list_registered_stages(self) -> List[StageMetadata]:
        """List metadata for all registered stages ordered by execution order."""
        with self._lock:
            return sorted(self._stages.values(), key=lambda s: s.execution_order)

    def record_stage_execution(self, name: str, latency_ms: float, success: bool = True) -> None:
        """Update stage execution metrics."""
        with self._lock:
            stage = self._stages.get(name)
            if stage:
                stage.execution_count += 1
                if stage.execution_count == 1:
                    stage.average_latency_ms = latency_ms
                else:
                    stage.average_latency_ms = (stage.average_latency_ms * 0.9) + (latency_ms * 0.1)
                stage.health_state = "HEALTHY" if success else "DEGRADED"

    def statistics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_registered_stages": len(self._stages),
                "enabled_stages_count": sum(1 for s in self._stages.values() if s.enabled),
            }

    def health(self) -> Dict[str, Any]:
        return {"status": "HEALTHY", "ready": True}

    def metrics(self) -> Dict[str, Any]:
        with self._lock:
            avg_lat = sum(s.average_latency_ms for s in self._stages.values()) / len(self._stages) if self._stages else 0.0
            return {"average_overall_stage_latency_ms": round(avg_lat, 3)}
