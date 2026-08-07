"""Release Planner for Enterprise Release Management Framework v1.0."""

from __future__ import annotations

import time
from threading import RLock
from typing import Any
from app.release.release_models import ReleaseStage


class ReleasePlanner:
    """Planner managing multi-stage release rollout progressions (Alpha -> GA)."""

    def __init__(self):
        self._lock = RLock()
        self._current_stage: ReleaseStage = ReleaseStage.GENERAL_AVAILABILITY
        self._plans: list[dict[str, Any]] = []

    def get_current_stage(self) -> ReleaseStage:
        with self._lock:
            return self._current_stage

    def promote_stage(self, next_stage: ReleaseStage) -> ReleaseStage:
        with self._lock:
            self._current_stage = next_stage
            self._plans.append({"stage": str(next_stage), "timestamp": time.time()})
            return self._current_stage

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "current_stage": str(self._current_stage),
                "total_promotions": len(self._plans),
            }

    def health(self) -> dict[str, Any]:
        return {"status": "HEALTHY", "ready": True}

    def metrics(self) -> dict[str, Any]:
        return {"stage_compliance_rate": 100.0}
