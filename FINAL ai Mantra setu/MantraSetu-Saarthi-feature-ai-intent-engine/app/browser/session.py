"""Browser Session Manager for MantraSetu AgentOS.

This module implements BrowserSessionManager for controlling browser session lifecycles,
runtime instances, and thread-safe session registration without performing browser actions or
navigation operations.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import UUID

from app.browser.base import (
    BaseBrowserSession,
    BrowserRuntimeHandle,
    BrowserSessionError,
    SessionResourceNotFoundError,
)
from app.browser.models import BrowserSession, BrowserSessionStatus


def _utc_now() -> datetime:
    """Return the current timestamp in UTC.

    Returns:
        datetime: Current timezone-aware datetime instance in UTC.
    """
    return datetime.now(timezone.utc)


@dataclass
class _RuntimeSession:
    """Private dataclass encapsulating runtime placeholders for a session.

    Attributes:
        session_id: Unique session identifier UUID.
        created_at: Creation timestamp in UTC.
        browser: Placeholder for browser instance.
        context: Placeholder for browser context instance.
        page: Placeholder for active page instance.
    """

    session_id: UUID
    created_at: datetime
    browser: Any | None = None
    context: Any | None = None
    page: Any | None = None


class BrowserSessionManager(BaseBrowserSession):
    """Thread-safe session manager implementing BaseBrowserSession contract.

    Responsibility:
        Manages browser session creation, retrieval, listing, runtime tracking, and closure.
        Does not execute browser action commands or page navigation.

    Lifecycle Archiving Policy:
        Closed sessions remain stored in `_sessions` with status `BrowserSessionStatus.CLOSED`
        to preserve session metadata for auditing and history queries, while their active
        runtime drivers in `_runtimes` are completely destroyed and purged.
    """

    def __init__(self, browser_factory: Callable[..., Any] | None = None) -> None:
        """Initialize BrowserSessionManager with optional runtime factory and thread-safe lock.

        Args:
            browser_factory: Optional injectable factory for creating runtime browser instances.
        """
        self._browser_factory = browser_factory
        self._sessions: dict[UUID, BrowserSession] = {}
        self._runtimes: dict[UUID, _RuntimeSession] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Verify that the session manager has been initialized.

        Raises:
            BrowserSessionError: If the manager is not initialized.
        """
        if not self._initialized:
            raise BrowserSessionError(
                "BrowserSessionManager is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize the session manager runtime state."""
        async with self._lock:
            self._initialized = True

    async def close(self) -> None:
        """Close all managed browser sessions and destroy runtime resources."""
        async with self._lock:
            session_ids = list(self._sessions.keys())
            for session_id in session_ids:
                try:
                    runtime = self._runtimes.get(session_id)
                    if runtime:
                        await self._destroy_runtime(runtime)
                except Exception as e:
                    raise BrowserSessionError(
                        f"Failed to destroy runtime for session {session_id}: {str(e)}"
                    ) from e

            self._runtimes.clear()
            for sid, sess in self._sessions.items():
                self._sessions[sid] = sess.model_copy(
                    update={
                        "status": BrowserSessionStatus.CLOSED,
                        "updated_at": _utc_now(),
                    }
                )
            self._initialized = False

    async def create_session(
        self,
        user_agent: str | None = None,
        viewport_width: int = 1280,
        viewport_height: int = 720,
    ) -> BrowserSession:
        """Create and register a new thread-safe BrowserSession.

        Args:
            user_agent: Optional custom User-Agent string.
            viewport_width: Viewport width in pixels.
            viewport_height: Viewport height in pixels.

        Returns:
            BrowserSession: Created session model.

        Raises:
            BrowserSessionError: If manager is uninitialized or session creation fails.
        """
        self._ensure_initialized()
        async with self._lock:
            try:
                session = BrowserSession(
                    status=BrowserSessionStatus.ACTIVE,
                    user_agent=user_agent,
                    viewport_width=viewport_width,
                    viewport_height=viewport_height,
                )
                runtime = self._create_runtime(session.session_id)

                self._sessions[session.session_id] = session
                self._runtimes[session.session_id] = runtime

                return session
            except Exception as e:
                raise BrowserSessionError(f"Failed to create browser session: {str(e)}") from e

    async def get_session(self, session_id: UUID) -> BrowserSession | None:
        """Retrieve an active or stored browser session by identifier.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            BrowserSession | None: Session model if found, None otherwise.

        Raises:
            BrowserSessionError: If manager is uninitialized.
        """
        self._ensure_initialized()
        async with self._lock:
            return self._sessions.get(session_id)

    async def get_runtime_handle(self, session_id: UUID) -> BrowserRuntimeHandle | None:
        """Retrieve the public runtime handle for an active browser session.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            BrowserRuntimeHandle | None: Public runtime handle model if active, None otherwise.

        Raises:
            BrowserSessionError: If manager is uninitialized.
        """
        self._ensure_initialized()
        async with self._lock:
            runtime = self._runtimes.get(session_id)
            if not runtime:
                return None
            return BrowserRuntimeHandle(
                session_id=runtime.session_id,
                browser=runtime.browser,
                context=runtime.context,
                page=runtime.page,
            )

    async def close_session(self, session_id: UUID) -> None:
        """Close and release runtime resources for a browser session by identifier.

        Archiving Behavior:
            The session remains archived in `_sessions` with status `CLOSED`, but its
            active runtime driver in `_runtimes` is destroyed and purged.

        Args:
            session_id: Unique session identifier UUID to close.

        Raises:
            SessionResourceNotFoundError: If the session ID is not registered.
            BrowserSessionError: If manager is uninitialized or cleanup fails.
        """
        self._ensure_initialized()
        async with self._lock:
            if session_id not in self._sessions:
                raise SessionResourceNotFoundError(f"Session {session_id} does not exist.")

            try:
                runtime = self._runtimes.pop(session_id, None)
                if runtime:
                    await self._destroy_runtime(runtime)

                existing = self._sessions[session_id]
                closed_session = existing.model_copy(
                    update={
                        "status": BrowserSessionStatus.CLOSED,
                        "updated_at": _utc_now(),
                    }
                )
                self._sessions[session_id] = closed_session
            except Exception as e:
                raise BrowserSessionError(
                    f"Failed to close browser session {session_id}: {str(e)}"
                ) from e

    async def list_sessions(self) -> tuple[BrowserSession, ...]:
        """List all managed browser session instances.

        Returns:
            tuple[BrowserSession, ...]: Tuple of BrowserSession objects.

        Raises:
            BrowserSessionError: If manager is uninitialized.
        """
        self._ensure_initialized()
        async with self._lock:
            return tuple(self._sessions.values())

    async def health_check(self) -> bool:
        """Check operational health of the session manager.

        Returns:
            bool: True if initialized and functional, False otherwise.
        """
        return self._initialized

    def _create_runtime(self, session_id: UUID) -> _RuntimeSession:
        """Internal helper to instantiate runtime driver placeholders for a session.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            _RuntimeSession: Private runtime session dataclass instance.
        """
        browser_inst = self._browser_factory() if self._browser_factory else None
        return _RuntimeSession(
            session_id=session_id,
            created_at=_utc_now(),
            browser=browser_inst,
            context=None,
            page=None,
        )

    async def _destroy_runtime(self, runtime: _RuntimeSession) -> None:
        """Internal helper to asynchronously release runtime driver resources for a session.

        Args:
            runtime: Private runtime session instance to destroy.
        """
        runtime.browser = None
        runtime.context = None
        runtime.page = None
