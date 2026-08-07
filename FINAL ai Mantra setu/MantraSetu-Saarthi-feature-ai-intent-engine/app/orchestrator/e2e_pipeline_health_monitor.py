"""Pipeline Health Monitor for Enterprise AgentOS Pipeline v1.1."""

from __future__ import annotations

import time
from threading import RLock
from typing import Any, Dict


class PipelineHealthMonitor:
    """Monitor tracking real-time pipeline success rates, stage latencies, retries, and SLA metrics."""

    def __init__(self):
        self._lock = RLock()
        self._total_pipeline_runs = 0
        self._successful_pipeline_runs = 0
        self._failed_pipeline_runs = 0
        self._total_stage_latency_ms = 0.0
        self._total_stages_executed = 0
        self._failed_stage_count = 0
        self._retry_count = 0
        self._recovery_success_count = 0

    def record_pipeline_execution(self, duration_ms: float, success: bool, stages_count: int = 22) -> None:
        """Record pipeline execution metrics."""
        with self._lock:
            self._total_pipeline_runs += 1
            if success:
                self._successful_pipeline_runs += 1
            else:
                self._failed_pipeline_runs += 1
            self._total_stage_latency_ms += duration_ms
            self._total_stages_executed += stages_count

    def record_stage_result(self, latency_ms: float, success: bool, retries: int = 0, recovered: bool = False) -> None:
        """Record stage-level execution metrics."""
        with self._lock:
            self._retry_count += retries
            if not success and not recovered:
                self._failed_stage_count += 1
            if recovered:
                self._recovery_success_count += 1

    def statistics(self) -> Dict[str, Any]:
        with self._lock:
            succ_rate = (self._successful_pipeline_runs / self._total_pipeline_runs * 100.0) if self._total_pipeline_runs > 0 else 100.0
            return {
                "total_pipeline_runs": self._total_pipeline_runs,
                "successful_pipeline_runs": self._successful_pipeline_runs,
                "failed_pipeline_runs": self._failed_pipeline_runs,
                "pipeline_success_rate": round(succ_rate, 2),
                "failed_stage_count": self._failed_stage_count,
                "retry_count": self._retry_count,
            }

    def health(self) -> Dict[str, Any]:
        with self._lock:
            status = "HEALTHY"
            if self._failed_pipeline_runs > 0 and self._total_pipeline_runs > 0:
                failure_rate = (self._failed_pipeline_runs / self._total_pipeline_runs) * 100.0
                if failure_rate > 5.0:
                    status = "DEGRADED"
            return {"status": status, "ready": True}

    def metrics(self) -> Dict[str, Any]:
        with self._lock:
            avg_latency = (self._total_stage_latency_ms / self._total_pipeline_runs) if self._total_pipeline_runs > 0 else 0.0
            rec_rate = (self._recovery_success_count / (self._failed_stage_count + self._recovery_success_count) * 100.0) if (self._failed_stage_count + self._recovery_success_count) > 0 else 100.0
            return {
                "average_pipeline_latency_ms": round(avg_latency, 3),
                "average_stage_latency_ms": round(avg_latency / 22.0 if avg_latency > 0 else 0.2, 3),
                "recovery_success_rate": round(rec_rate, 2),
                "total_retries": self._retry_count,
            }
