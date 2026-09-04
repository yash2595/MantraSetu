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
    pending_booking: dict[str, Any] | None = None
    pending_kundali: dict[str, Any] | None = None
    pending_muhurat: dict[str, Any] | None = None
    current_page: str = "/"
    current_field: str | None = None
    lock: Any = field(default_factory=__import__('asyncio').Lock)

    def update_location(self, page: str | None = None, field: str | None = None) -> None:
        """Update session location and field tracking state."""
        if page is not None:
            self.current_page = page
        if field is not None:
            self.current_field = field


class AISessionManager:
    """Manager tracking AI session lifecycle, conversation mapping, and session restoration without mutating NavigationStateStore."""

    def __init__(self, session_ttl_seconds: float = 3600.0) -> None:
        self._session_ttl_seconds = session_ttl_seconds
        self._sessions: dict[str, AISessionRecord] = {}
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._sessions_created_count = 0
        self._last_cleanup_ts = 0.0

    def cleanup_expired_sessions(self, force: bool = False) -> int:
        """Purge sessions inactive longer than session_ttl_seconds."""
        with self._lock:
            now_ts = time.time()
            if not force and (now_ts - self._last_cleanup_ts < 60.0):
                return 0
            self._last_cleanup_ts = now_ts

            now = datetime.now(timezone.utc)
            expired_ids = []
            for sid, rec in list(self._sessions.items()):
                try:
                    last_active = datetime.fromisoformat(rec.last_active_at)
                    idle_seconds = (now - last_active).total_seconds()
                    if idle_seconds > self._session_ttl_seconds:
                        expired_ids.append((sid, idle_seconds))
                except Exception:
                    pass

            for sid, idle_sec in expired_ids:
                self._sessions.pop(sid, None)
                logger.info(
                    "[AI-SESSION-CLEANUP] Purged expired AI session %s (idle for %.1fs > TTL %.1fs)",
                    sid,
                    idle_sec,
                    self._session_ttl_seconds,
                )
            return len(expired_ids)

    def get_or_create_session(self, session_id: str, conversation_id: str = "") -> AISessionRecord:
        """Retrieve existing or initialize new AI session record."""
        with self._lock:
            self.cleanup_expired_sessions()
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
