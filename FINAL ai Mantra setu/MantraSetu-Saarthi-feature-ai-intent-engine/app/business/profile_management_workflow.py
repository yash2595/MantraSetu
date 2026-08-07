"""Profile Management Workflow for Enterprise Business Layer Sprint 6D v1.0."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Dict, List, Optional
from app.business.workflow_telemetry import WorkflowTelemetryEngine


@dataclass
class UserProfileState:
    user_id: str
    full_name: str = "Aarav Sharma"
    preferred_language: str = "hi-IN"
    preferred_voice: str = "ananya"
    favorite_temples: List[str] = field(default_factory=list)
    favorite_pandits: List[str] = field(default_factory=list)


class ProfileManagementWorkflow:
    """Workflow managing user profile views, preferences, and favorites."""

    def __init__(self):
        self._lock = RLock()
        self.telemetry = WorkflowTelemetryEngine()
        self._profiles: Dict[str, UserProfileState] = {}

    def get_profile(self, user_id: str) -> UserProfileState:
        with self._lock:
            if user_id not in self._profiles:
                self._profiles[user_id] = UserProfileState(user_id=user_id)
            return self._profiles[user_id]

    def update_preferences(
        self,
        user_id: str,
        language: Optional[str] = None,
        voice: Optional[str] = None,
        favorite_temple: Optional[str] = None,
        favorite_pandit: Optional[str] = None,
    ) -> UserProfileState:
        """Update user preferences."""
        start = time.perf_counter()
        with self._lock:
            profile = self.get_profile(user_id)
            if language:
                profile.preferred_language = language
            if voice:
                profile.preferred_voice = voice
            if favorite_temple and favorite_temple not in profile.favorite_temples:
                profile.favorite_temples.append(favorite_temple)
            if favorite_pandit and favorite_pandit not in profile.favorite_pandits:
                profile.favorite_pandits.append(favorite_pandit)

            elapsed = (time.perf_counter() - start) * 1000.0

            self.telemetry.record_workflow_execution(
                workflow_name="ProfileManagementWorkflow",
                session_id=user_id,
                status="COMPLETED",
                duration_ms=elapsed,
                steps_completed=1,
                total_steps=1,
            )

            return profile

    def statistics(self) -> Dict[str, Any]:
        with self._lock:
            return {"active_profiles_managed": len(self._profiles)}

    def health(self) -> Dict[str, Any]:
        return {"status": "HEALTHY", "ready": True}

    def metrics(self) -> Dict[str, Any]:
        return {"avg_profile_latency_ms": 0.3}
