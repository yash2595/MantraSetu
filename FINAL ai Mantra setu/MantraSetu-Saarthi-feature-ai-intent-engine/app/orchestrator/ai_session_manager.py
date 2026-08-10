"""AI Session Manager for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "AISessionManager"
_COMPONENT_VERSION = "4.1"


@dataclass
class AISessionRecord:
    """Session lifecycle record."""

    session_id: str
    conversation_id: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_active_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    active_requests: set[str] = field(default_factory=set)
    onboarding_state: dict[str, Any] | None = None


class AISessionManager:
    """Manager tracking AI session lifecycle, conversation mapping, and session restoration without mutating NavigationStateStore."""

    def __init__(self, session_ttl_seconds: float = 3600.0) -> None:
        self._session_ttl_seconds = session_ttl_seconds
        self._sessions: dict[str, AISessionRecord] = {}
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._sessions_created_count = 0

    def get_or_create_session(self, session_id: str, conversation_id: str = "") -> AISessionRecord:
        """Retrieve existing or initialize new AI session record."""
        with self._lock:
            if session_id not in self._sessions:
                conv_id = conversation_id or f"conv_{session_id}"
                rec = AISessionRecord(session_id=session_id, conversation_id=conv_id)
                self._sessions[session_id] = rec
                self._sessions_created_count += 1

            rec = self._sessions[session_id]
            rec.last_active_at = datetime.now(timezone.utc).isoformat()
            return rec

    def bind_request(self, session_id: str, request_id: str) -> None:
        """Bind an active request ID to a session."""
        with self._lock:
            rec = self.get_or_create_session(session_id)
            rec.active_requests.add(request_id)

    def unbind_request(self, session_id: str, request_id: str) -> None:
        """Unbind a request ID from a session."""
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].active_requests.discard(request_id)

    # ------------------------------------------------------------------
    # Diagnostics, Telemetry & Health
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return session manager statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "active_sessions_count": len(self._sessions),
                "sessions_created_count": self._sessions_created_count,
                "thread_safe": True,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose performance metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            message="AISessionManager operational.",
        )
