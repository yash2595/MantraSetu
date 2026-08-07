"""Abstract contracts and interfaces for the Conversation subsystem in MantraSetu AgentOS.

This module defines the foundational BaseConversationManager abstract interface
and domain exception hierarchy for managing conversation sessions and messages.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Mapping
from uuid import UUID

from app.ai.models import (
    Conversation,
    Message,
)
from app.core.models import ComponentHealth


class ConversationError(Exception):
    """Base exception for all conversation subsystem errors."""

    pass


class ConversationResourceNotFoundError(ConversationError):
    """Raised when a requested conversation session or resource cannot be found."""

    pass


class ConversationStorageError(ConversationError):
    """Raised when a conversation storage or retrieval operation fails."""

    pass


class ConversationClosedError(ConversationError):
    """Raised when attempting an operation on a closed conversation session."""

    pass


class ConversationMemoryError(ConversationError):
    """Raised when memory storage or retrieval operations fail."""

    pass


class ConversationContextError(ConversationError):
    """Raised when conversation context validation or updates fail."""

    pass


class ConversationValidationError(ConversationError):
    """Raised when message or turn parameter validation fails."""

    pass


class ConversationInitializationError(ConversationError):
    """Raised when component initialization fails."""

    pass


class BaseConversationManager(ABC):
    """Abstract interface defining the contract for conversation, message, and session management."""

    @abstractmethod
    async def create_conversation(
        self,
        user_id: UUID | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> Conversation:
        """Create and persist a new Conversation session entity.

        Args:
            user_id: Optional user identifier UUID.
            metadata: Optional key-value metadata mapping.

        Returns:
            Conversation: Newly created Conversation model.
        """
        ...

    @abstractmethod
    async def get_conversation(self, conversation_id: UUID) -> Conversation:
        """Retrieve a Conversation session model by identifier.

        Args:
            conversation_id: Unique conversation identifier UUID.

        Returns:
            Conversation: Retrieved Conversation model.

        Raises:
            ConversationResourceNotFoundError: If conversation_id is not found.
        """
        ...

    @abstractmethod
    async def add_message(
        self,
        conversation_id: UUID,
        message: Message,
    ) -> Conversation:
        """Append a Message object to an active Conversation session.

        Args:
            conversation_id: Unique conversation identifier UUID.
            message: Message object to append.

        Returns:
            Conversation: Updated Conversation model.

        Raises:
            ConversationResourceNotFoundError: If conversation_id is not found.
        """
        ...

    @abstractmethod
    async def get_messages(
        self,
        conversation_id: UUID,
        limit: int | None = None,
    ) -> tuple[Message, ...]:
        """Retrieve chronological Message objects for a conversation.

        Args:
            conversation_id: Unique conversation identifier UUID.
            limit: Optional maximum number of recent messages to retrieve.

        Returns:
            tuple[Message, ...]: Immutable tuple of Message objects.

        Raises:
            ConversationResourceNotFoundError: If conversation_id is not found.
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close conversation manager resources and release connection pools."""
        ...

    @abstractmethod
    async def health_check(self) -> ComponentHealth:
        """Perform an operational health check on the conversation manager component.

        Returns:
            ComponentHealth: Operational component health status model.
        """
        ...
