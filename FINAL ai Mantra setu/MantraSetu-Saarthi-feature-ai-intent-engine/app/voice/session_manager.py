"""VoiceSessionManager owning lifecycle operations for active voice sessions."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any
from uuid import UUID

from app.voice.session import VoiceSession, VoiceSessionStatus

logger = logging.getLogger(__name__)


class VoiceSessionManager:
    """Thread-safe single owner of active concurrent VoiceSession objects."""

    def __init__(self) -> None:
        self._sessions: dict[str, VoiceSession] = {}
        self._connection_index: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def create_session(
        self,
        connection_id: str,
        conversation_id: UUID | None = None,
        language: str = "hi",
        sample_rate: int = 16000,
        audio_encoding: Any = "pcm16",
        session_id: str | None = None,
    ) -> VoiceSession:
        """Create and register a new active VoiceSession, or reuse an existing one if session_id matches."""
        async with self._lock:
            if session_id and session_id in self._sessions:
                session = self._sessions[session_id]
                session.connection_id = connection_id
                self._connection_index[connection_id] = session_id
                session.touch()
                logger.info("VoiceSession reconnected/reused", extra={"session_id": session_id, "connection_id": connection_id})
                return session

            session = VoiceSession(
                connection_id=connection_id,
                conversation_id=conversation_id,
                language=language,
                sample_rate=sample_rate,
                audio_encoding=audio_encoding,
            )
            if session_id:
                session.session_id = session_id
            self._sessions[session.session_id] = session
            self._connection_index[connection_id] = session.session_id
            logger.info("VoiceSession created", extra={"session_id": session.session_id, "connection_id": connection_id})
            return session

    async def get_session(self, session_or_connection_id: str) -> VoiceSession | None:
        """Retrieve active VoiceSession by session_id or connection_id."""
        async with self._lock:
            if session_or_connection_id in self._sessions:
                return self._sessions[session_or_connection_id]
            session_id = self._connection_index.get(session_or_connection_id)
            if session_id:
                return self._sessions.get(session_id)
            return None

    async def remove_session(self, session_id: str) -> VoiceSession | None:
        """Remove a VoiceSession from registry."""
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                self._connection_index.pop(session.connection_id, None)
                logger.info("VoiceSession removed", extra={"session_id": session_id})
            return session

    async def close_session(
        self,
        session_id: str,
        status: VoiceSessionStatus = VoiceSessionStatus.CLOSED,
    ) -> VoiceSession | None:
        """Mark session closed and clean up registry."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.status = status
                session.touch()
                self._sessions.pop(session_id, None)
                self._connection_index.pop(session.connection_id, None)
                logger.info("VoiceSession closed", extra={"session_id": session_id, "status": status.value})
            return session

    async def cleanup_disconnected_sessions(self, timeout_seconds: float = 300.0) -> int:
        """Purge stale sessions inactive longer than timeout_seconds."""
        async with self._lock:
            now = datetime.now(timezone.utc)
            stale_ids = [
                sid for sid, sess in self._sessions.items()
                if (now - sess.updated_at).total_seconds() >= timeout_seconds
            ]
            for sid in stale_ids:
                sess = self._sessions.pop(sid, None)
                if sess:
                    self._connection_index.pop(sess.connection_id, None)
            if stale_ids:
                logger.info("Cleaned up stale VoiceSessions", extra={"purged_count": len(stale_ids)})
            return len(stale_ids)
