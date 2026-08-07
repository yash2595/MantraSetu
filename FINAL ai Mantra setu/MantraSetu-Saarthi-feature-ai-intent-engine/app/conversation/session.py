"""Conversation Session Manager module for MantraSetu AgentOS.

This module implements ConversationSessionManager and BaseSessionManager for managing conversation session lifecycles,
thread-safe registration, context assignment, and session status transitions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from datetime import datetime, timezone
from uuid import UUID

from app.conversation.base import (
    ConversationClosedError,
    ConversationError,
    ConversationInitializationError,
    ConversationResourceNotFoundError,
    ConversationValidationError,
)
from app.conversation.models import (
    ConversationContext,
    ConversationSession,
    ConversationSessionStatus,
)
from app.core.models import ComponentHealth, SystemHealthStatus


def _utc_now() -> datetime:
    """Return the current timestamp in UTC.

    Returns:
        datetime: Current timezone-aware datetime instance in UTC.
    """
    return datetime.now(timezone.utc)


class BaseSessionManager(ABC):
    """Abstract interface defining the contract for conversation session lifecycle management."""

    @abstractmethod
    async def create_session(
        self,
        user_id: UUID | None = None,
        conversation_id: UUID | None = None,
        context: ConversationContext | None = None,
    ) -> ConversationSession:
        """Create and register a new ConversationSession instance.

        Args:
            user_id: Optional user identifier UUID.
            conversation_id: Optional conversation identifier UUID.
            context: Optional ConversationContext configuration.

        Returns:
            ConversationSession: Created session entity.
        """
        ...

    @abstractmethod
    async def get_session(self, session_id: UUID) -> ConversationSession:
        """Retrieve a ConversationSession instance by identifier.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            ConversationSession: Retrieved session entity.

        Raises:
            ConversationResourceNotFoundError: If session_id is not found.
        """
        ...

    @abstractmethod
    async def update_context(
        self,
        session_id: UUID,
        context: ConversationContext,
    ) -> ConversationSession:
        """Update active ConversationContext for a session.

        Args:
            session_id: Unique session identifier UUID.
            context: New ConversationContext instance.

        Returns:
            ConversationSession: Updated session entity.

        Raises:
            ConversationResourceNotFoundError: If session_id is not found.
            ConversationClosedError: If session is closed or archived.
        """
        ...

    @abstractmethod
    async def close_session(self, session_id: UUID) -> ConversationSession:
        """Close and archive a ConversationSession by identifier.

        Args:
            session_id: Unique session identifier UUID to close.

        Returns:
            ConversationSession: Closed session entity.

        Raises:
            ConversationResourceNotFoundError: If session_id is not found.
            ConversationClosedError: If session is already closed.
        """
        ...

    @abstractmethod
    async def health_check(self) -> ComponentHealth:
        """Perform an operational health check on the session manager.

        Returns:
            ComponentHealth: Component health status model.
        """
        ...


# Alias for backward compatibility
BaseConversationSession = BaseSessionManager


class ConversationSessionManager(BaseSessionManager):
    """Thread-safe in-memory conversation session manager implementing BaseSessionManager contract.

    Responsibility:
        Manages creation, retrieval, context updating, and lifecycle closing of ConversationSession
        objects without embedding AI prompt logic, database queries, or memory storage.
    """

    def __init__(self) -> None:
        """Initialize ConversationSessionManager with internal registry and thread-safe lock."""
        self._sessions: dict[UUID, ConversationSession] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the session manager has been initialized.

        Raises:
            ConversationInitializationError: If manager is uninitialized.
        """
        if not self._initialized:
            raise ConversationInitializationError(
                "ConversationSessionManager is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize session manager runtime state. Idempotent."""
        async with self._lock:
            if self._initialized:
                return
            self._initialized = True

    async def close(self) -> None:
        """Close all managed conversation sessions and clear internal storage."""
        async with self._lock:
            for sid, session in list(self._sessions.items()):
                if session.status == ConversationSessionStatus.ACTIVE:
                    self._sessions[sid] = session.model_copy(
                        update={
                            "status": ConversationSessionStatus.CLOSED,
                            "updated_at": _utc_now(),
                        }
                    )
            self._sessions.clear()
            self._initialized = False

    async def create_session(
        self,
        user_id: UUID | None = None,
        conversation_id: UUID | None = None,
        context: ConversationContext | None = None,
    ) -> ConversationSession:
        """Create and register a new thread-safe ConversationSession.

        Args:
            user_id: Optional associated user UUID.
            conversation_id: Optional associated conversation UUID.
            context: Optional ConversationContext configuration.

        Returns:
            ConversationSession: Created conversation session model.

        Raises:
            ConversationInitializationError: If manager is uninitialized.
        """
        self._require_initialized()
        async with self._lock:
            session = ConversationSession(
                user_id=user_id,
                conversation_id=conversation_id,
                status=ConversationSessionStatus.ACTIVE,
                context=context or ConversationContext(),
            )
            self._sessions[session.session_id] = session
            return session

    async def get_session(self, session_id: UUID) -> ConversationSession:
        """Retrieve a conversation session by identifier.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            ConversationSession: Session model if found.

        Raises:
            ConversationInitializationError: If manager is uninitialized.
            ConversationResourceNotFoundError: If session_id does not exist.
        """
        self._require_initialized()
        if not isinstance(session_id, UUID):
            raise ConversationValidationError("Invalid session_id UUID provided.")

        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise ConversationResourceNotFoundError(
                    f"Conversation session '{session_id}' not found."
                )
            return session

    async def update_context(
        self,
        session_id: UUID,
        context: ConversationContext,
    ) -> ConversationSession:
        """Update active conversation context settings for a session.

        Args:
            session_id: Unique session identifier UUID.
            context: New ConversationContext instance.

        Returns:
            ConversationSession: Updated conversation session model.

        Raises:
            ConversationInitializationError: If manager is uninitialized.
            ConversationResourceNotFoundError: If session_id does not exist.
            ConversationClosedError: If session is closed or archived.
        """
        self._require_initialized()
        if not isinstance(context, ConversationContext):
            raise ConversationValidationError("Invalid ConversationContext instance provided.")

        async with self._lock:
            existing = self._sessions.get(session_id)
            if not existing:
                raise ConversationResourceNotFoundError(
                    f"Conversation session '{session_id}' not found."
                )

            if existing.status in (
                ConversationSessionStatus.CLOSED,
                ConversationSessionStatus.ARCHIVED,
            ):
                raise ConversationClosedError(
                    f"Conversation session '{session_id}' is already closed or archived."
                )

            updated = existing.model_copy(
                update={
                    "context": context,
                    "updated_at": _utc_now(),
                }
            )
            self._sessions[session_id] = updated
            return updated

    async def close_session(self, session_id: UUID) -> ConversationSession:
        """Close and archive a conversation session by identifier.

        Args:
            session_id: Unique session identifier UUID to close.

        Returns:
            ConversationSession: Closed conversation session model.

        Raises:
            ConversationInitializationError: If manager is uninitialized.
            ConversationResourceNotFoundError: If session_id does not exist.
            ConversationClosedError: If session is already closed.
        """
        self._require_initialized()
        async with self._lock:
            existing = self._sessions.get(session_id)
            if not existing:
                raise ConversationResourceNotFoundError(
                    f"Conversation session '{session_id}' not found."
                )

            if existing.status in (
                ConversationSessionStatus.CLOSED,
                ConversationSessionStatus.ARCHIVED,
            ):
                raise ConversationClosedError(
                    f"Conversation session '{session_id}' is already closed."
                )

            closed_session = existing.model_copy(
                update={
                    "status": ConversationSessionStatus.CLOSED,
                    "updated_at": _utc_now(),
                }
            )
            self._sessions[session_id] = closed_session
            return closed_session

    async def list_sessions(self) -> tuple[ConversationSession, ...]:
        """List all managed conversation session instances.

        Returns:
            tuple[ConversationSession, ...]: Immutable tuple of ConversationSession objects.

        Raises:
            ConversationInitializationError: If manager is uninitialized.
        """
        self._require_initialized()
        async with self._lock:
            return tuple(self._sessions.values())

    async def health_check(self) -> ComponentHealth:
        """Check operational health of the session manager.

        Returns:
            ComponentHealth: Operational component health model.
        """
        return ComponentHealth(
            component_name="session_manager",
            status=SystemHealthStatus.HEALTHY if self._initialized else SystemHealthStatus.UNHEALTHY,
            message="ConversationSessionManager operational."
            if self._initialized
            else "ConversationSessionManager uninitialized.",
        )
