"""Conversation Manager coordinator for MantraSetu AgentOS.

This module implements ConversationManager for coordinating conversation session lifecycle operations
and memory operations through dependency-injected session and memory managers.
"""

from __future__ import annotations

from uuid import UUID

from app.conversation.base import (
    ConversationError,
    ConversationInitializationError,
    ConversationResourceNotFoundError,
    ConversationValidationError,
)
from app.conversation.memory import BaseConversationMemory
from app.conversation.models import (
    ConversationContext,
    ConversationMessage,
    ConversationSession,
)
from app.conversation.session import BaseSessionManager
from app.core.models import ComponentHealth, SystemHealthStatus


class ConversationManager:
    """Coordinator facade service delegating session and memory operations.

    Responsibility:
        Coordinates session creation, retrieval, context management, message persistence,
        and memory clearing through injected BaseSessionManager and BaseConversationMemory contracts.
    """

    def __init__(
        self,
        session_manager: BaseSessionManager,
        memory_manager: BaseConversationMemory,
    ) -> None:
        """Initialize ConversationManager with injected session and memory managers.

        Args:
            session_manager: Injected BaseSessionManager instance.
            memory_manager: Injected BaseConversationMemory instance.
        """
        self._session_manager = session_manager
        self._memory_manager = memory_manager
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the conversation manager has been initialized.

        Raises:
            ConversationInitializationError: If manager is uninitialized.
        """
        if not self._initialized:
            raise ConversationInitializationError(
                "ConversationManager is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize underlying session manager and memory components. Idempotent."""
        if self._initialized:
            return

        if hasattr(self._session_manager, "initialize"):
            await self._session_manager.initialize()
        if hasattr(self._memory_manager, "initialize"):
            await self._memory_manager.initialize()

        self._initialized = True

    async def close(self) -> None:
        """Close underlying memory and session manager components."""
        if hasattr(self._memory_manager, "close"):
            await self._memory_manager.close()
        if hasattr(self._session_manager, "close"):
            await self._session_manager.close()

        self._initialized = False

    async def create_conversation(
        self,
        user_id: UUID | None = None,
        conversation_id: UUID | None = None,
        context: ConversationContext | None = None,
    ) -> ConversationSession:
        """Create a new conversation session delegating to session_manager.

        Args:
            user_id: Optional user identifier UUID.
            conversation_id: Optional conversation identifier UUID.
            context: Optional ConversationContext configuration.

        Returns:
            ConversationSession: Created conversation session model.
        """
        self._require_initialized()
        try:
            return await self._session_manager.create_session(
                user_id=user_id,
                conversation_id=conversation_id,
                context=context,
            )
        except ConversationError:
            raise
        except Exception as e:
            raise ConversationError(f"Failed to create conversation: {str(e)}") from e

    async def get_conversation(
        self,
        session_id: UUID,
    ) -> ConversationSession:
        """Retrieve a conversation session by identifier delegating to session_manager.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            ConversationSession: Retrieved conversation session model.
        """
        self._require_initialized()
        try:
            return await self._session_manager.get_session(session_id)
        except ConversationError:
            raise
        except Exception as e:
            raise ConversationError(f"Failed to get conversation '{session_id}': {str(e)}") from e

    async def add_message(
        self,
        session_id: UUID,
        message: ConversationMessage,
    ) -> None:
        """Store a ConversationMessage for a session delegating to memory_manager.

        Args:
            session_id: Unique session identifier UUID.
            message: ConversationMessage model instance.
        """
        self._require_initialized()
        try:
            await self._memory_manager.store_message(session_id=session_id, message=message)
        except ConversationError:
            raise
        except Exception as e:
            raise ConversationError(f"Failed to add message for session '{session_id}': {str(e)}") from e

    async def get_messages(
        self,
        session_id: UUID,
        limit: int | None = None,
    ) -> tuple[ConversationMessage, ...]:
        """Retrieve chronological messages for a session delegating to memory_manager.

        Args:
            session_id: Unique session identifier UUID.
            limit: Optional limit on recent messages count.

        Returns:
            tuple[ConversationMessage, ...]: Immutable tuple of ConversationMessage objects.
        """
        self._require_initialized()
        try:
            return await self._memory_manager.get_messages(session_id=session_id, limit=limit)
        except ConversationError:
            raise
        except Exception as e:
            raise ConversationError(f"Failed to get messages for session '{session_id}': {str(e)}") from e

    async def update_context(
        self,
        session_id: UUID,
        context: ConversationContext,
    ) -> ConversationContext:
        """Update active context for a session delegating to memory_manager.

        Args:
            session_id: Unique session identifier UUID.
            context: ConversationContext instance.

        Returns:
            ConversationContext: Updated conversation context entity.
        """
        self._require_initialized()
        try:
            return await self._memory_manager.update_context(session_id=session_id, context=context)
        except ConversationError:
            raise
        except Exception as e:
            raise ConversationError(f"Failed to update context for session '{session_id}': {str(e)}") from e

    async def get_context(
        self,
        session_id: UUID,
    ) -> ConversationContext:
        """Retrieve active context for a session delegating to memory_manager.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            ConversationContext: Active conversation context entity.
        """
        self._require_initialized()
        try:
            return await self._memory_manager.get_context(session_id=session_id)
        except ConversationError:
            raise
        except Exception as e:
            raise ConversationError(f"Failed to get context for session '{session_id}': {str(e)}") from e

    async def close_conversation(
        self,
        session_id: UUID,
    ) -> ConversationSession:
        """Close a conversation session delegating to session_manager.

        Args:
            session_id: Unique session identifier UUID to close.

        Returns:
            ConversationSession: Closed conversation session entity.
        """
        self._require_initialized()
        try:
            return await self._session_manager.close_session(session_id=session_id)
        except ConversationError:
            raise
        except Exception as e:
            raise ConversationError(f"Failed to close conversation '{session_id}': {str(e)}") from e

    async def clear_memory(
        self,
        session_id: UUID,
    ) -> None:
        """Purge all recorded messages and context delegating to memory_manager.

        Args:
            session_id: Unique session identifier UUID to clear.
        """
        self._require_initialized()
        try:
            await self._memory_manager.clear_memory(session_id=session_id)
        except ConversationError:
            raise
        except Exception as e:
            raise ConversationError(f"Failed to clear memory for session '{session_id}': {str(e)}") from e

    async def health_check(self) -> ComponentHealth:
        """Check aggregated operational health across session manager and memory manager.

        Returns:
            ComponentHealth: Aggregated component health status model.
        """
        if not self._initialized:
            return ComponentHealth(
                component_name="conversation_manager",
                status=SystemHealthStatus.UNHEALTHY,
                message="ConversationManager uninitialized.",
            )

        sess_health = await self._session_manager.health_check()
        mem_health = await self._memory_manager.health_check()

        is_healthy = (
            isinstance(sess_health, ComponentHealth)
            and sess_health.status == SystemHealthStatus.HEALTHY
            and isinstance(mem_health, ComponentHealth)
            and mem_health.status == SystemHealthStatus.HEALTHY
        )

        return ComponentHealth(
            component_name="conversation_manager",
            status=SystemHealthStatus.HEALTHY if is_healthy else SystemHealthStatus.UNHEALTHY,
            message="ConversationManager operational."
            if is_healthy
            else "ConversationManager component degraded.",
        )
