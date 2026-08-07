"""In-memory session storage layer for MantraSetu AgentOS.

This module implements SessionStore, a thread-safe, in-memory storage manager
for UserSession models using asyncio primitives without external database dependencies.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

from app.session.base import (
    SessionInitializationError,
    SessionResourceNotFoundError,
    SessionValidationError,
)
from app.session.models import UserSession


class SessionStore:
    """Thread-safe in-memory UserSession storage manager.

    Responsibility:
        Provides thread-safe persistence, retrieval, updating, existence checking, and deletion
        of UserSession instances without database or external cache dependencies.
    """

    def __init__(self) -> None:
        """Initialize SessionStore with internal dictionary registry and asyncio lock."""
        self._sessions: dict[UUID, UserSession] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the session store has been initialized.

        Raises:
            SessionInitializationError: If initialize() has not been called.
        """
        if not self._initialized:
            raise SessionInitializationError(
                "SessionStore is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize session store runtime state. Idempotent."""
        async with self._lock:
            if self._initialized:
                return
            self._initialized = True

    async def close(self) -> None:
        """Close session store and clear all internal entries."""
        async with self._lock:
            self._sessions.clear()
            self._initialized = False

    async def save(self, session: UserSession) -> None:
        """Store a new UserSession model instance.

        Args:
            session: UserSession instance to store.

        Raises:
            SessionInitializationError: If store is uninitialized.
            SessionValidationError: If session is invalid.
        """
        self._require_initialized()
        if not isinstance(session, UserSession):
            raise SessionValidationError("Invalid UserSession instance provided.")

        async with self._lock:
            self._sessions[session.session_id] = session

    async def get(self, session_id: UUID) -> UserSession:
        """Retrieve a UserSession model by identifier.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            UserSession: Retrieved session entity.

        Raises:
            SessionInitializationError: If store is uninitialized.
            SessionResourceNotFoundError: If session_id does not exist.
        """
        self._require_initialized()
        if not isinstance(session_id, UUID):
            raise SessionValidationError("Invalid session_id UUID provided.")

        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise SessionResourceNotFoundError(f"UserSession '{session_id}' not found.")
            return session

    async def update(self, session: UserSession) -> None:
        """Update an existing UserSession model in store.

        Args:
            session: UserSession instance with updated fields.

        Raises:
            SessionInitializationError: If store is uninitialized.
            SessionResourceNotFoundError: If session.session_id is not found in store.
            SessionValidationError: If session parameter is invalid.
        """
        self._require_initialized()
        if not isinstance(session, UserSession):
            raise SessionValidationError("Invalid UserSession instance provided.")

        async with self._lock:
            if session.session_id not in self._sessions:
                raise SessionResourceNotFoundError(f"UserSession '{session.session_id}' not found.")
            self._sessions[session.session_id] = session

    async def delete(self, session_id: UUID) -> None:
        """Delete a UserSession by identifier.

        Args:
            session_id: Unique session identifier UUID to delete.

        Raises:
            SessionInitializationError: If store is uninitialized.
            SessionResourceNotFoundError: If session_id is not found.
        """
        self._require_initialized()
        if not isinstance(session_id, UUID):
            raise SessionValidationError("Invalid session_id UUID provided.")

        async with self._lock:
            if session_id not in self._sessions:
                raise SessionResourceNotFoundError(f"UserSession '{session_id}' not found.")
            del self._sessions[session_id]

    async def exists(self, session_id: UUID) -> bool:
        """Check if a UserSession exists in store by identifier.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            bool: True if session exists, False otherwise.

        Raises:
            SessionInitializationError: If store is uninitialized.
        """
        self._require_initialized()
        if not isinstance(session_id, UUID):
            raise SessionValidationError("Invalid session_id UUID provided.")

        async with self._lock:
            return session_id in self._sessions

    async def list_sessions(self) -> tuple[UserSession, ...]:
        """Retrieve all currently stored UserSession instances.

        Returns:
            tuple[UserSession, ...]: Immutable tuple of UserSession models.

        Raises:
            SessionInitializationError: If store is uninitialized.
        """
        self._require_initialized()
        async with self._lock:
            return tuple(self._sessions.values())

    async def clear(self) -> None:
        """Purge all stored session instances from memory.

        Raises:
            SessionInitializationError: If store is uninitialized.
        """
        self._require_initialized()
        async with self._lock:
            self._sessions.clear()
