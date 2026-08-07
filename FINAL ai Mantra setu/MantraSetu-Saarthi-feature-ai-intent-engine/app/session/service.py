"""Application Session Service facade for MantraSetu AgentOS.

This module implements SessionService as the main application service facade
exposing user session lifecycle operations, state tracking, and session context management.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Mapping
from uuid import UUID

from app.core.models import ComponentHealth, SystemHealthStatus
from app.session.base import (
    SessionError,
    SessionInitializationError,
    SessionResourceNotFoundError,
    SessionValidationError,
)
from app.session.models import (
    SessionContext,
    SessionStatus,
    UserSession,
)
from app.session.store import SessionStore


def _utc_now() -> datetime:
    """Return the current timestamp in UTC.

    Returns:
        datetime: Current timezone-aware datetime instance in UTC.
    """
    return datetime.now(timezone.utc)


class SessionService:
    """Application facade service for user session lifecycle management.

    Responsibility:
        Coordinates user session creation, state retrieval, updating, closing, deletion,
        and session context management through an injected SessionStore without framework coupling.
    """

    def __init__(self, store: SessionStore) -> None:
        """Initialize SessionService with an injected SessionStore dependency.

        Args:
            store: Injected SessionStore instance.
        """
        self._store = store
        self._contexts: dict[UUID, SessionContext] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the session service has been initialized.

        Raises:
            SessionInitializationError: If service is uninitialized.
        """
        if not self._initialized:
            raise SessionInitializationError(
                "SessionService is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize session service and underlying store runtime state. Idempotent."""
        async with self._lock:
            if self._initialized:
                return

            if hasattr(self._store, "initialize"):
                await self._store.initialize()

            self._initialized = True

    async def close(self) -> None:
        """Close session service and release underlying store resources."""
        async with self._lock:
            if hasattr(self._store, "close"):
                await self._store.close()
            self._contexts.clear()
            self._initialized = False

    async def create_session(
        self,
        user_id: UUID | None = None,
        metadata: Mapping[str, object] | None = None,
        expires_at: datetime | None = None,
    ) -> UserSession:
        """Create and persist a new UserSession.

        Args:
            user_id: Optional associated user identifier UUID.
            metadata: Optional key-value metadata mapping.
            expires_at: Optional UTC expiration timestamp.

        Returns:
            UserSession: Created UserSession entity.

        Raises:
            SessionInitializationError: If service is uninitialized.
        """
        self._require_initialized()
        session = UserSession(
            user_id=user_id,
            status=SessionStatus.ACTIVE,
            metadata=metadata or {},
            expires_at=expires_at,
        )
        await self._store.save(session)
        return session

    async def get_session(self, session_id: UUID) -> UserSession:
        """Retrieve a UserSession model by identifier.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            UserSession: Retrieved session entity.

        Raises:
            SessionInitializationError: If service is uninitialized.
            SessionResourceNotFoundError: If session_id does not exist.
        """
        self._require_initialized()
        return await self._store.get(session_id)

    async def update_session(self, session: UserSession) -> UserSession:
        """Update an existing UserSession entity in store.

        Args:
            session: UserSession instance with updated values.

        Returns:
            UserSession: Updated session entity.

        Raises:
            SessionInitializationError: If service is uninitialized.
            SessionResourceNotFoundError: If session.session_id is not found.
        """
        self._require_initialized()
        await self._store.update(session)
        return session

    async def close_session(self, session_id: UUID) -> UserSession:
        """Transition a UserSession status to CLOSED.

        Args:
            session_id: Unique session identifier UUID to close.

        Returns:
            UserSession: Closed UserSession model.

        Raises:
            SessionInitializationError: If service is uninitialized.
            SessionResourceNotFoundError: If session_id is not found.
        """
        self._require_initialized()
        existing = await self._store.get(session_id)
        updated = existing.model_copy(
            update={
                "status": SessionStatus.CLOSED,
                "updated_at": _utc_now(),
            }
        )
        await self._store.update(updated)
        return updated

    async def delete_session(self, session_id: UUID) -> None:
        """Delete a UserSession and its associated context.

        Args:
            session_id: Unique session identifier UUID to delete.

        Raises:
            SessionInitializationError: If service is uninitialized.
            SessionResourceNotFoundError: If session_id is not found.
        """
        self._require_initialized()
        await self._store.delete(session_id)
        async with self._lock:
            self._contexts.pop(session_id, None)

    async def get_context(self, session_id: UUID) -> SessionContext:
        """Retrieve active SessionContext for a user session.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            SessionContext: Active context model.

        Raises:
            SessionInitializationError: If service is uninitialized.
            SessionResourceNotFoundError: If session_id does not exist.
        """
        self._require_initialized()
        if not await self._store.exists(session_id):
            raise SessionResourceNotFoundError(f"UserSession '{session_id}' not found.")

        async with self._lock:
            if session_id in self._contexts:
                return self._contexts[session_id]
            return SessionContext(session_id=session_id)

    async def update_context(
        self,
        session_id: UUID,
        context: SessionContext,
    ) -> SessionContext:
        """Update active SessionContext for a user session.

        Args:
            session_id: Unique session identifier UUID.
            context: SessionContext instance to set.

        Returns:
            SessionContext: Updated context model.

        Raises:
            SessionInitializationError: If service is uninitialized.
            SessionResourceNotFoundError: If session_id does not exist.
            SessionValidationError: If context instance is invalid.
        """
        self._require_initialized()
        if not isinstance(context, SessionContext):
            raise SessionValidationError("Invalid SessionContext instance provided.")

        if not await self._store.exists(session_id):
            raise SessionResourceNotFoundError(f"UserSession '{session_id}' not found.")

        async with self._lock:
            self._contexts[session_id] = context
            return context

    async def health_check(self) -> ComponentHealth:
        """Check operational health of the session service.

        Returns:
            ComponentHealth: Operational component health status model.
        """
        return ComponentHealth(
            component_name="session_service",
            status=SystemHealthStatus.HEALTHY if self._initialized else SystemHealthStatus.UNHEALTHY,
            message="SessionService operational."
            if self._initialized
            else "SessionService uninitialized.",
        )
