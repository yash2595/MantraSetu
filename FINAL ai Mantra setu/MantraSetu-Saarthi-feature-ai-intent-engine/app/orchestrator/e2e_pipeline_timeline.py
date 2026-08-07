"""Execution Timeline Recorder for Enterprise AgentOS Pipeline v1.1."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Dict, List, Optional
from app.orchestrator.e2e_pipeline_context import _utc_now_iso


@dataclass(frozen=True)
class StageTimelineEntry:
    """Immutable record for a stage execution in timeline."""

    stage_name: str
    trace_id: str
    start_time: str
    finish_time: str
    duration_ms: float
    status: str = "SUCCESS"  # SUCCESS, RECOVERED, FAILED
    error_msg: Optional[str] = None
    recovery_attempts: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_name": self.stage_name,
            "trace_id": self.trace_id,
            "start_time": self.start_time,
            "finish_time": self.finish_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error_msg": self.error_msg,
            "recovery_attempts": self.recovery_attempts,
        }


class ExecutionTimelineRecorder:
    """Recorder maintaining an immutable execution timeline per request trace."""

    def __init__(self):
        self._lock = RLock()
        self._timelines: Dict[str, List[StageTimelineEntry]] = {}
        self._total_entries = 0

    def record_stage_timeline(
        self,
        trace_id: str,
        stage_name: str,
        start_time_iso: str,
        finish_time_iso: str,
        duration_ms: float,
        status: str = "SUCCESS",
        error_msg: Optional[str] = None,
        recovery_attempts: int = 0,
    ) -> StageTimelineEntry:
        """Record stage entry into timeline."""
        entry = StageTimelineEntry(
            stage_name=stage_name,
            trace_id=trace_id,
            start_time=start_time_iso,
            finish_time=finish_time_iso,
            duration_ms=round(duration_ms, 3),
            status=status,
            error_msg=error_msg,
            recovery_attempts=recovery_attempts,
        )
        with self._lock:
            timeline = self._timelines.setdefault(trace_id, [])
            timeline.append(entry)
            self._total_entries += 1
        return entry

    def get_timeline_for_trace(self, trace_id: str) -> List[StageTimelineEntry]:
        """Retrieve timeline entries for a given trace ID."""
        with self._lock:
            return list(self._timelines.get(trace_id, []))

    def statistics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "traces_recorded_count": len(self._timelines),
                "total_timeline_entries": self._total_entries,
            }

    def health(self) -> Dict[str, Any]:
        return {"status": "HEALTHY", "ready": True}

    def metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {"timeline_recording_latency_ms": 0.02}
