"""Abstract contracts and interfaces for the Session subsystem in MantraSetu AgentOS.

This module defines abstract base classes for session lifecycle management, storage abstractions,
and health monitoring alongside domain exception hierarchies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Mapping
from uuid import UUID

from app.core.models import ComponentHealth
from app.session.models import SessionContext, SessionStatus, UserSession


class SessionError(Exception):
    """Base exception for all session subsystem errors."""

    pass


class SessionResourceNotFoundError(SessionError):
    """Raised when a requested session entity cannot be found."""

    pass


class SessionExpiredError(SessionError):
    """Raised when an operation is attempted on an expired session."""

    pass


class SessionStorageError(SessionError):
    """Raised when a session persistence or retrieval operation fails."""

    pass


class SessionValidationError(SessionError):
    """Raised when session input parameter validation fails."""

    pass


class SessionInitializationError(SessionError):
    """Raised when a session component initialization fails."""

    pass


class BaseSessionManager(ABC):
    """Abstract interface defining the contract for user session lifecycle management."""

    @abstractmethod
    async def create_session(
        self,
        user_id: UUID | None = None,
        metadata: Mapping[str, object] | None = None,
        expires_at: datetime | None = None,
    ) -> UserSession:
        """Create and persist a new UserSession entity.

        Args:
            user_id: Optional user identifier UUID.
            metadata: Optional key-value metadata mapping.
            expires_at: Optional UTC expiration timestamp.

        Returns:
            UserSession: Newly created UserSession model.
        """
        ...

    @abstractmethod
    async def get_session(self, session_id: UUID) -> UserSession:
        """Retrieve a UserSession model by identifier.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            UserSession: Retrieved UserSession model.

        Raises:
            SessionResourceNotFoundError: If session_id is not found.
            SessionExpiredError: If session has expired.
        """
        ...

    @abstractmethod
    async def update_session(
        self,
        session_id: UUID,
        metadata: Mapping[str, object] | None = None,
        status: SessionStatus | None = None,
    ) -> UserSession:
        """Update a UserSession entity's metadata or operational status.

        Args:
            session_id: Unique session identifier UUID.
            metadata: Optional updated metadata mapping.
            status: Optional updated SessionStatus enum.

        Returns:
            UserSession: Updated UserSession model.

        Raises:
            SessionResourceNotFoundError: If session_id is not found.
            SessionExpiredError: If session is expired.
        """
        ...

    @abstractmethod
    async def close_session(self, session_id: UUID) -> UserSession:
        """Transition a UserSession to CLOSED status.

        Args:
            session_id: Unique session identifier UUID to close.

        Returns:
            UserSession: Closed UserSession model.

        Raises:
            SessionResourceNotFoundError: If session_id is not found.
        """
        ...

    @abstractmethod
    async def delete_session(self, session_id: UUID) -> None:
        """Purge and delete a UserSession by identifier.

        Args:
            session_id: Unique session identifier UUID to delete.

        Raises:
            SessionResourceNotFoundError: If session_id is not found.
        """
        ...

    @abstractmethod
    async def health_check(self) -> ComponentHealth:
        """Perform an operational health check on the session manager component.

        Returns:
            ComponentHealth: Operational component health status model.
        """
        ...
