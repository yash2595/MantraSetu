"""Global Exception Recovery Coordinator for Enterprise AgentOS Pipeline v1.1."""

from __future__ import annotations

import time
from threading import RLock
from typing import Any, Dict, Optional
from app.orchestrator.e2e_pipeline_context import PipelineContext


class ExceptionCategory:
    TRANSIENT = "TRANSIENT"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"


class GlobalExceptionRecoveryCoordinator:
    """Centralized exception recovery engine for pipeline failures."""

    def __init__(self):
        self._lock = RLock()
        self._total_exceptions_handled = 0
        self._total_recoveries_successful = 0
        self._max_retries = 3

    def classify_exception(self, exception: Exception) -> str:
        """Classify exception severity category."""
        err_msg = str(exception).lower()
        if "timeout" in err_msg or "temporary" in err_msg or "rate limit" in err_msg:
            return ExceptionCategory.TRANSIENT
        elif "optional" in err_msg or "fallback" in err_msg:
            return ExceptionCategory.DEGRADED
        return ExceptionCategory.CRITICAL

    def determine_recovery_strategy(self, category: str, attempt: int) -> str:
        """Determine recovery strategy based on error classification."""
        if category == ExceptionCategory.TRANSIENT and attempt < self._max_retries:
            return "RETRY"
        elif category == ExceptionCategory.DEGRADED:
            return "CONTINUE_SAFE"
        elif category == ExceptionCategory.CRITICAL:
            return "ESCALATE"
        return "FALLBACK"

    def retry_if_allowed(self, attempt: int) -> bool:
        """Determine if retry is allowed."""
        return attempt < self._max_retries

    def continue_if_safe(self, stage_name: str) -> bool:
        """Determine if safe to continue pipeline with warning for non-critical stage."""
        non_critical_stages = ["RAG Retrieval", "TTS Audio Generation", "Memory Persistence"]
        return stage_name in non_critical_stages

    def handle_stage_failure(self, stage_name: str, exception: Exception, context: PipelineContext, attempt: int = 1) -> Dict[str, Any]:
        """Process stage failure and execute recovery strategy."""
        with self._lock:
            self._total_exceptions_handled += 1
            cat = self.classify_exception(exception)
            strategy = self.determine_recovery_strategy(cat, attempt)

            recovered = False
            if strategy == "RETRY" and self.retry_if_allowed(attempt):
                recovered = True
            elif strategy == "CONTINUE_SAFE" or self.continue_if_safe(stage_name):
                recovered = True
                strategy = "CONTINUE_SAFE"

            if recovered:
                self._total_recoveries_successful += 1

            return {
                "stage": stage_name,
                "category": cat,
                "strategy": strategy,
                "recovered": recovered,
                "error_message": str(exception),
            }

    def statistics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_exceptions_handled": self._total_exceptions_handled,
                "total_recoveries_successful": self._total_recoveries_successful,
            }

    def health(self) -> Dict[str, Any]:
        return {"status": "HEALTHY", "ready": True}

    def metrics(self) -> Dict[str, Any]:
        with self._lock:
            rate = (self._total_recoveries_successful / self._total_exceptions_handled * 100.0) if self._total_exceptions_handled > 0 else 100.0
            return {
                "recovery_success_rate": round(rate, 2),
                "max_retries_configured": self._max_retries,
            }
