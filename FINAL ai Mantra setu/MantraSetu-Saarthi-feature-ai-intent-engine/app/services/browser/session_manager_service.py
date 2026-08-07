"""Default implementation of the Browser Session Manager."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.services.browser.driver_base import BrowserDriver
from app.services.browser.session_manager_base import (
    BrowserSessionManager,
    BrowserSessionManagerError,
    DuplicateSessionError,
    SessionClosedError,
    SessionNotFoundError,
)
from app.services.browser.session_manager_models import (
    BrowserSession,
    SessionStatus,
)

logger = logging.getLogger(__name__)


class DefaultBrowserSessionManager(BrowserSessionManager):
    """Manages browser sessions in-memory.
    
    Ensures async thread-safe access to a dictionary registry.
    Delegates browser resource creation to the injected BrowserDriver.
    """

    def __init__(self, driver: BrowserDriver) -> None:
        """Initialize the session manager.
        
        Args:
            driver: The low-level browser driver used to create/close resources.
        """
        self._driver = driver
        self._registry: dict[str, BrowserSession] = {}
        self._lock = asyncio.Lock()

    async def create_session(self, session_id: str) -> BrowserSession:
        """Create a new browser session, generating browser resources."""
        if not session_id or not session_id.strip():
            raise BrowserSessionManagerError("session_id cannot be empty.")

        async with self._lock:
            if session_id in self._registry:
                raise DuplicateSessionError(f"Session already exists: {session_id}")

            logger.info("Creating browser resources for session | session_id=%s", session_id)
            
            # Delegate entirely to the Driver to manage physical resources
            await self._driver.connect()
            await self._driver.create_session(session_id)

            now = datetime.now(timezone.utc)
            session = BrowserSession(
                session_id=session_id,
                status=SessionStatus.ACTIVE,
                created_at=now,
                last_used_at=now,
                metadata={},
            )
            
            self._registry[session_id] = session
            logger.info("Session created | session_id=%s", session_id)
            return session

    async def get_session(self, session_id: str) -> BrowserSession:
        """Retrieve an existing session."""
        if not session_id or not session_id.strip():
            raise BrowserSessionManagerError("session_id cannot be empty.")

        async with self._lock:
            session = self._registry.get(session_id)
            if not session:
                raise SessionNotFoundError(f"Session not found: {session_id}")
            
            logger.info("Session retrieved | session_id=%s", session_id)
            return session

    async def session_exists(self, session_id: str) -> bool:
        """Check if a session exists."""
        if not session_id or not session_id.strip():
            raise BrowserSessionManagerError("session_id cannot be empty.")
            
        async with self._lock:
            exists = session_id in self._registry
            return exists

    async def touch_session(self, session_id: str) -> BrowserSession:
        """Update the last used timestamp for a session."""
        if not session_id or not session_id.strip():
            raise BrowserSessionManagerError("session_id cannot be empty.")

        async with self._lock:
            session = self._registry.get(session_id)
            if not session:
                raise SessionNotFoundError(f"Session not found: {session_id}")
            
            if session.status == SessionStatus.CLOSED:
                raise SessionClosedError(f"Cannot touch closed session: {session_id}")

            # Rebuild immutable model with updated timestamp
            now = datetime.now(timezone.utc)
            updated_session = BrowserSession(
                session_id=session.session_id,
                status=session.status,
                created_at=session.created_at,
                last_used_at=now,
                metadata=session.metadata,
            )
            
            self._registry[session_id] = updated_session
            logger.info("Session touched | session_id=%s", session_id)
            return updated_session

    async def close_session(self, session_id: str) -> None:
        """Close browser resources and remove the session."""
        if not session_id or not session_id.strip():
            raise BrowserSessionManagerError("session_id cannot be empty.")

        async with self._lock:
            session = self._registry.get(session_id)
            if not session:
                raise SessionNotFoundError(f"Session not found: {session_id}")

            logger.info("Closing browser resources for session | session_id=%s", session_id)
            
            try:
                # Delegate entirely to the Driver to clean up resources
                await self._driver.close_session(session_id)
            except Exception as e:
                logger.warning("Error releasing browser resources for session %s: %s", session_id, str(e))
                
            del self._registry[session_id]
            logger.info("Session closed | session_id=%s", session_id)

    async def close_all_sessions(self) -> None:
        """Close all tracked sessions."""
        async with self._lock:
            session_ids = list(self._registry.keys())
            
        for sid in session_ids:
            try:
                await self.close_session(sid)
            except SessionNotFoundError:
                pass
        
        logger.info("All sessions closed")

    async def cleanup_idle_sessions(self, timeout_seconds: int) -> None:
        """Clean up sessions that have been idle for too long."""
        if timeout_seconds <= 0:
            raise BrowserSessionManagerError("timeout_seconds must be strictly positive.")

        now = datetime.now(timezone.utc)
        expired_ids = []

        async with self._lock:
            for sid, session in self._registry.items():
                if session.status == SessionStatus.CLOSED:
                    continue
                    
                idle_duration = (now - session.last_used_at).total_seconds()
                if idle_duration > timeout_seconds:
                    expired_ids.append(sid)

        for sid in expired_ids:
            try:
                await self.close_session(sid)
                logger.info("Session expired and cleaned up | session_id=%s", sid)
            except SessionNotFoundError:
                pass
                
        logger.info("Cleanup completed | expired_count=%d", len(expired_ids))
