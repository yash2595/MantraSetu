"""Conversation Memory module for MantraSetu AgentOS.

This module provides BaseConversationMemory and InMemoryConversationMemory for managing
short-term conversation memory, message storage, context persistence, and memory clearing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from uuid import UUID

from app.conversation.base import (
    ConversationInitializationError,
    ConversationMemoryError,
    ConversationResourceNotFoundError,
    ConversationValidationError,
)
from app.conversation.models import (
    ConversationContext,
    ConversationMessage,
)
from app.core.models import ComponentHealth, SystemHealthStatus


class BaseConversationMemory(ABC):
    """Abstract interface defining the contract for short-term conversation memory storage."""

    @abstractmethod
    async def store_message(
        self,
        session_id: UUID,
        message: ConversationMessage,
    ) -> None:
        """Store a ConversationMessage for a session.

        Args:
            session_id: Unique session identifier UUID.
            message: ConversationMessage model instance to record.
        """
        ...

    @abstractmethod
    async def get_messages(
        self,
        session_id: UUID,
        limit: int | None = None,
    ) -> tuple[ConversationMessage, ...]:
        """Retrieve chronological ConversationMessage instances for a session.

        Args:
            session_id: Unique session identifier UUID.
            limit: Optional maximum number of recent messages to retrieve.

        Returns:
            tuple[ConversationMessage, ...]: Immutable tuple of ConversationMessage objects.
        """
        ...

    @abstractmethod
    async def update_context(
        self,
        session_id: UUID,
        context: ConversationContext,
    ) -> ConversationContext:
        """Update active ConversationContext for a session.

        Args:
            session_id: Unique session identifier UUID.
            context: ConversationContext instance.

        Returns:
            ConversationContext: Updated conversation context entity.
        """
        ...

    @abstractmethod
    async def get_context(
        self,
        session_id: UUID,
    ) -> ConversationContext:
        """Retrieve active ConversationContext for a session.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            ConversationContext: Active conversation context entity.
        """
        ...

    @abstractmethod
    async def clear_memory(
        self,
        session_id: UUID,
    ) -> None:
        """Purge all stored messages and context for a session.

        Args:
            session_id: Unique session identifier UUID to clear.
        """
        ...

    @abstractmethod
    async def health_check(self) -> ComponentHealth:
        """Perform an operational health check on the memory storage component.

        Returns:
            ComponentHealth: Component health status model.
        """
        ...


class InMemoryConversationMemory(BaseConversationMemory):
    """Thread-safe in-memory conversation storage implementing BaseConversationMemory.

    Responsibility:
        Manages chronological persistence, retrieval, context updating, and clearing of ConversationMessage
        objects and ConversationContext instances associated with session identifiers.
    """

    def __init__(self) -> None:
        """Initialize InMemoryConversationMemory with internal storage registries and thread-safe lock."""
        self._messages: dict[UUID, list[ConversationMessage]] = {}
        self._contexts: dict[UUID, ConversationContext] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the memory component has been initialized.

        Raises:
            ConversationInitializationError: If memory is uninitialized.
        """
        if not self._initialized:
            raise ConversationInitializationError(
                "InMemoryConversationMemory is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize memory storage runtime state. Idempotent."""
        async with self._lock:
            if self._initialized:
                return
            self._initialized = True

    async def close(self) -> None:
        """Close memory storage, clear all recorded messages/contexts, and release resources."""
        async with self._lock:
            self._messages.clear()
            self._contexts.clear()
            self._initialized = False

    async def store_message(
        self,
        session_id: UUID,
        message: ConversationMessage,
    ) -> None:
        """Store a ConversationMessage for a session in chronological order.

        Args:
            session_id: Unique session identifier UUID.
            message: ConversationMessage model instance to record.

        Raises:
            ConversationInitializationError: If memory is uninitialized.
            ConversationValidationError: If session_id or message is invalid.
        """
        self._require_initialized()
        if not isinstance(session_id, UUID):
            raise ConversationValidationError("Invalid session_id UUID provided.")
        if not isinstance(message, ConversationMessage):
            raise ConversationValidationError("Invalid ConversationMessage instance provided.")

        async with self._lock:
            if session_id not in self._messages:
                self._messages[session_id] = []
            self._messages[session_id].append(message)

    async def get_messages(
        self,
        session_id: UUID,
        limit: int | None = None,
    ) -> tuple[ConversationMessage, ...]:
        """Retrieve chronological ConversationMessage instances for a session.

        Args:
            session_id: Unique session identifier UUID.
            limit: Optional maximum number of recent messages to retrieve.

        Returns:
            tuple[ConversationMessage, ...]: Immutable tuple of ConversationMessage objects.

        Raises:
            ConversationInitializationError: If memory is uninitialized.
            ConversationValidationError: If limit is negative or session_id is invalid.
        """
        self._require_initialized()
        if not isinstance(session_id, UUID):
            raise ConversationValidationError("Invalid session_id UUID provided.")
        if limit is not None and limit <= 0:
            raise ConversationValidationError("Limit parameter must be a positive integer.")

        async with self._lock:
            msgs = self._messages.get(session_id, [])
            if limit is not None and len(msgs) > limit:
                return tuple(msgs[-limit:])
            return tuple(msgs)

    async def update_context(
        self,
        session_id: UUID,
        context: ConversationContext,
    ) -> ConversationContext:
        """Update active ConversationContext for a session.

        Args:
            session_id: Unique session identifier UUID.
            context: ConversationContext instance.

        Returns:
            ConversationContext: Updated conversation context model.

        Raises:
            ConversationInitializationError: If memory is uninitialized.
            ConversationValidationError: If session_id or context is invalid.
        """
        self._require_initialized()
        if not isinstance(session_id, UUID):
            raise ConversationValidationError("Invalid session_id UUID provided.")
        if not isinstance(context, ConversationContext):
            raise ConversationValidationError("Invalid ConversationContext instance provided.")

        async with self._lock:
            self._contexts[session_id] = context
            return context

    async def get_context(
        self,
        session_id: UUID,
    ) -> ConversationContext:
        """Retrieve active ConversationContext for a session.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            ConversationContext: Active conversation context model.

        Raises:
            ConversationInitializationError: If memory is uninitialized.
            ConversationValidationError: If session_id is invalid.
        """
        self._require_initialized()
        if not isinstance(session_id, UUID):
            raise ConversationValidationError("Invalid session_id UUID provided.")

        async with self._lock:
            if session_id in self._contexts:
                return self._contexts[session_id]
            return ConversationContext(session_id=session_id)

    async def clear_memory(
        self,
        session_id: UUID,
    ) -> None:
        """Purge all recorded messages and context for a session.

        Args:
            session_id: Unique session identifier UUID to clear.

        Raises:
            ConversationInitializationError: If memory is uninitialized.
            ConversationValidationError: If session_id is invalid.
        """
        self._require_initialized()
        if not isinstance(session_id, UUID):
            raise ConversationValidationError("Invalid session_id UUID provided.")

        async with self._lock:
            self._messages.pop(session_id, None)
            self._contexts.pop(session_id, None)

    async def health_check(self) -> ComponentHealth:
        """Check operational health of the memory storage component.

        Returns:
            ComponentHealth: Operational component health status model.
        """
        return ComponentHealth(
            component_name="conversation_memory",
            status=SystemHealthStatus.HEALTHY if self._initialized else SystemHealthStatus.UNHEALTHY,
            message="InMemoryConversationMemory operational."
            if self._initialized
            else "InMemoryConversationMemory uninitialized.",
        )


# Alias for backward compatibility
ConversationMemory = InMemoryConversationMemory
