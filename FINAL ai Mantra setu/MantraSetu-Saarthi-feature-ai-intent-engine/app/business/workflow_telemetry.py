"""Workflow Telemetry Engine for Enterprise Business Workflows Sprint 6D v1.0."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, List, Optional
from uuid import uuid4


def _utc_now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 string format."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class WorkflowTelemetryRecord:
    """Telemetry record tracking a business workflow execution."""

    record_id: str = field(default_factory=lambda: str(uuid4()))
    workflow_name: str = "PujaBookingWorkflow"
    session_id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "COMPLETED"  # STARTED, COMPLETED, FAILED, RESUMED, CANCELLED
    duration_ms: float = 0.0
    steps_completed: int = 0
    total_steps: int = 5
    interrupted: bool = False
    error_msg: Optional[str] = None
    timestamp: str = field(default_factory=_utc_now_iso)


class WorkflowTelemetryEngine:
    """Thread-safe telemetry engine tracking workflow completion rates, latencies, pause/resume counts, and failures."""

    def __init__(self):
        self._lock = RLock()
        self._records: List[WorkflowTelemetryRecord] = []
        self._total_workflows_started = 0
        self._total_workflows_completed = 0
        self._total_workflows_resumed = 0

    def record_workflow_execution(
        self,
        workflow_name: str,
        session_id: str,
        status: str = "COMPLETED",
        duration_ms: float = 0.0,
        steps_completed: int = 0,
        total_steps: int = 5,
        interrupted: bool = False,
        error_msg: Optional[str] = None,
    ) -> WorkflowTelemetryRecord:
        rec = WorkflowTelemetryRecord(
            workflow_name=workflow_name,
            session_id=session_id,
            status=status,
            duration_ms=round(duration_ms, 3),
            steps_completed=steps_completed,
            total_steps=total_steps,
            interrupted=interrupted,
            error_msg=error_msg,
        )

        with self._lock:
            self._records.append(rec)
            self._total_workflows_started += 1
            if status == "COMPLETED":
                self._total_workflows_completed += 1
            elif status == "RESUMED":
                self._total_workflows_resumed += 1

        return rec

    def statistics(self) -> Dict[str, Any]:
        with self._lock:
            comp_rate = (self._total_workflows_completed / self._total_workflows_started * 100.0) if self._total_workflows_started > 0 else 100.0
            return {
                "total_workflows_started": self._total_workflows_started,
                "total_workflows_completed": self._total_workflows_completed,
                "total_workflows_resumed": self._total_workflows_resumed,
                "completion_rate_percentage": round(comp_rate, 2),
            }

    def health(self) -> Dict[str, Any]:
        return {"status": "HEALTHY", "ready": True}

    def metrics(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._records)
            avg_duration = (sum(r.duration_ms for r in self._records) / total) if total > 0 else 0.0
            return {
                "average_workflow_latency_ms": round(avg_duration, 3),
                "workflow_telemetry_active": True,
            }
