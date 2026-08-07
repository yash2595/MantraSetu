"""AI Provider Telemetry Engine for Enterprise AI Layer Sprint 6B v1.0."""

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
class AITelemetryRecord:
    """Telemetry record for an AI provider invocation."""

    record_id: str = field(default_factory=lambda: str(uuid4()))
    provider_id: str = "openai_gpt4o"
    category: str = "LLM"  # LLM, EMBEDDING, STT, TTS
    model_name: str = "gpt-4o"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    latency_ms: float = 0.0
    success: bool = True
    error_msg: Optional[str] = None
    timestamp: str = field(default_factory=_utc_now_iso)


class ProviderTelemetryEngine:
    """Thread-safe telemetry engine tracking token usage, costs, latencies, and failures across AI providers."""

    def __init__(self):
        self._lock = RLock()
        self._records: List[AITelemetryRecord] = []
        self._provider_stats: Dict[str, Dict[str, Any]] = {}

    def record_invocation(
        self,
        provider_id: str,
        category: str,
        model_name: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        estimated_cost: float = 0.0,
        latency_ms: float = 0.0,
        success: bool = True,
        error_msg: Optional[str] = None,
    ) -> AITelemetryRecord:
        """Record an AI provider invocation."""
        rec = AITelemetryRecord(
            provider_id=provider_id,
            category=category,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost=round(estimated_cost, 6),
            latency_ms=round(latency_ms, 3),
            success=success,
            error_msg=error_msg,
        )

        with self._lock:
            self._records.append(rec)
            stats = self._provider_stats.setdefault(
                provider_id,
                {
                    "total_requests": 0,
                    "successful_requests": 0,
                    "failed_requests": 0,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "total_latency_ms": 0.0,
                },
            )
            stats["total_requests"] += 1
            if success:
                stats["successful_requests"] += 1
            else:
                stats["failed_requests"] += 1
            stats["total_tokens"] += rec.total_tokens
            stats["total_cost"] += estimated_cost
            stats["total_latency_ms"] += latency_ms

        return rec

    def statistics(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._records)
            total_tokens = sum(r.total_tokens for r in self._records)
            total_cost = sum(r.estimated_cost for r in self._records)
            return {
                "total_ai_requests_recorded": total,
                "total_tokens_consumed": total_tokens,
                "total_cost_usd": round(total_cost, 6),
                "providers_tracked_count": len(self._provider_stats),
            }

    def health(self) -> Dict[str, Any]:
        return {"status": "HEALTHY", "ready": True}

    def metrics(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._records)
            avg_latency = (sum(r.latency_ms for r in self._records) / total) if total > 0 else 0.0
            succ_rate = (sum(1 for r in self._records if r.success) / total * 100.0) if total > 0 else 100.0
            return {
                "average_ai_latency_ms": round(avg_latency, 3),
                "ai_success_rate_percentage": round(succ_rate, 2),
            }
