"""Release Telemetry Engine for Enterprise Production Validation Framework v1.0."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import RLock
from typing import Any
from app.release.release_models import _utc_now_iso


@dataclass
class ReleaseTelemetrySample:
    """Telemetry sample for a release validation execution."""

    validator_name: str
    profile: str
    duration_ms: float
    passed: bool
    score: float = 100.0
    issues_found: int = 0
    timestamp: str = field(default_factory=_utc_now_iso)


class ReleaseTelemetryEngine:
    """Thread-safe telemetry recorder for validation operations."""

    _instance: ReleaseTelemetryEngine | None = None
    _lock: RLock = RLock()

    def __new__(cls) -> ReleaseTelemetryEngine:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._samples: list[ReleaseTelemetrySample] = []
            return cls._instance

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            if cls._instance:
                cls._instance._samples.clear()

    def record_sample(
        self,
        validator_name: str,
        profile: str,
        duration_ms: float,
        passed: bool,
        score: float = 100.0,
        issues_found: int = 0,
    ) -> ReleaseTelemetrySample:
        sample = ReleaseTelemetrySample(
            validator_name=validator_name,
            profile=profile,
            duration_ms=round(duration_ms, 3),
            passed=passed,
            score=score,
            issues_found=issues_found,
        )
        with self._lock:
            self._samples.append(sample)
        return sample

    def get_telemetry_summary(self) -> dict[str, Any]:
        with self._lock:
            total = len(self._samples)
            if total == 0:
                return {"total_validations": 0, "pass_rate": 100.0}

            passed_count = sum(1 for s in self._samples if s.passed)
            avg_duration = sum(s.duration_ms for s in self._samples) / total
            return {
                "total_validations": total,
                "passed_count": passed_count,
                "failed_count": total - passed_count,
                "pass_rate_percentage": round((passed_count / total) * 100.0, 2),
                "avg_duration_ms": round(avg_duration, 3),
            }

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {"total_telemetry_samples": len(self._samples)}

    def health(self) -> dict[str, Any]:
        return {"status": "HEALTHY", "ready": True}

    def metrics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "sample_buffer_size": len(self._samples),
                "export_latency_ms": 0.05,
            }

