"""Conversation Application Service facade for MantraSetu AgentOS.

This module implements ConversationService as the main application facade exposing
conversation operations and coordinating ConversationManager with optional AI interaction context.
"""

from __future__ import annotations

from uuid import UUID

from app.ai.models import (
    AIRequest,
    Message as AIMessage,
    MessageRole as AIMessageRole,
)
from app.ai.service import AIService
from app.conversation.base import (
    ConversationError,
    ConversationInitializationError,
    ConversationValidationError,
)
from app.conversation.manager import ConversationManager
from app.conversation.models import (
    ConversationContext,
    ConversationMessage,
    ConversationRole,
    ConversationSession,
)
from app.core.models import ComponentHealth, SystemHealthStatus


class ConversationService:
    """Application service facade for conversation lifecycle and AI context orchestration.

    Responsibility:
        Coordinates conversation sessions, message persistence, context management, and optional
        AI response generation via AIService without directly executing LLM inference or provider SDKs.
    """

    def __init__(
        self,
        conversation_manager: ConversationManager,
        ai_service: AIService | None = None,
    ) -> None:
        """Initialize ConversationService with strictly typed injected dependencies.

        Args:
            conversation_manager: Injected ConversationManager instance.
            ai_service: Optional injected AIService instance for AI response generation.
        """
        self._conversation_manager = conversation_manager
        self._ai_service = ai_service
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the conversation service has been initialized.

        Raises:
            ConversationInitializationError: If service is uninitialized.
        """
        if not self._initialized:
            raise ConversationInitializationError(
                "ConversationService is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize conversation service and underlying manager dependencies. Idempotent."""
        if self._initialized:
            return

        if hasattr(self._conversation_manager, "initialize"):
            await self._conversation_manager.initialize()
        if self._ai_service is not None and hasattr(self._ai_service, "initialize"):
            await self._ai_service.initialize()

        self._initialized = True

    async def close(self) -> None:
        """Close conversation service and release manager resources."""
        if hasattr(self._conversation_manager, "close"):
            await self._conversation_manager.close()

        self._initialized = False

    async def create_session(
        self,
        user_id: UUID | None = None,
        conversation_id: UUID | None = None,
        context: ConversationContext | None = None,
    ) -> ConversationSession:
        """Create a new managed conversation session delegating to conversation_manager.

        Args:
            user_id: Optional user identifier UUID.
            conversation_id: Optional conversation identifier UUID.
            context: Optional ConversationContext configuration.

        Returns:
            ConversationSession: Created session entity.
        """
        self._require_initialized()
        try:
            return await self._conversation_manager.create_conversation(
                user_id=user_id,
                conversation_id=conversation_id,
                context=context,
            )
        except ConversationError:
            raise
        except Exception as e:
            raise ConversationError(f"Failed to create conversation session: {str(e)}") from e

    async def send_message(
        self,
        session_id: UUID,
        message: ConversationMessage,
    ) -> ConversationMessage | None:
        """Send a user message, persist it, and generate an AI response if AI service is present.

        Args:
            session_id: Unique session identifier UUID.
            message: Incoming ConversationMessage model instance.

        Returns:
            ConversationMessage | None: Generated assistant message if AI service exists, None otherwise.
        """
        self._require_initialized()
        try:
            # 1. Store user message through ConversationManager
            await self._conversation_manager.add_message(session_id=session_id, message=message)

            # 2. If AI service exists, request AI response and store assistant reply
            if self._ai_service is not None:
                ai_req = AIRequest(
                    message=AIMessage(
                        role=AIMessageRole.USER,
                        content=message.content,
                    ),
                    conversation_id=session_id,
                )
                ai_response = await self._ai_service.generate(ai_req)
                assistant_msg = ConversationMessage(
                    session_id=session_id,
                    role=ConversationRole.ASSISTANT,
                    content=ai_response.content,
                )
                await self._conversation_manager.add_message(
                    session_id=session_id,
                    message=assistant_msg,
                )
                return assistant_msg

            return None
        except ConversationError:
            raise
        except Exception as e:
            raise ConversationError(f"Failed to send message for session '{session_id}': {str(e)}") from e

    async def get_history(
        self,
        session_id: UUID,
        limit: int | None = None,
    ) -> tuple[ConversationMessage, ...]:
        """Retrieve chronological message history delegating to conversation_manager.

        Args:
            session_id: Unique session identifier UUID.
            limit: Optional maximum number of recent messages.

        Returns:
            tuple[ConversationMessage, ...]: Immutable tuple of ConversationMessage objects.
        """
        self._require_initialized()
        try:
            return await self._conversation_manager.get_messages(session_id=session_id, limit=limit)
        except ConversationError:
            raise
        except Exception as e:
            raise ConversationError(f"Failed to get message history for session '{session_id}': {str(e)}") from e

    async def update_context(
        self,
        session_id: UUID,
        context: ConversationContext,
    ) -> ConversationContext:
        """Update active conversation context delegating to conversation_manager.

        Args:
            session_id: Unique session identifier UUID.
            context: ConversationContext instance.

        Returns:
            ConversationContext: Updated conversation context entity.
        """
        self._require_initialized()
        try:
            return await self._conversation_manager.update_context(session_id=session_id, context=context)
        except ConversationError:
            raise
        except Exception as e:
            raise ConversationError(f"Failed to update context for session '{session_id}': {str(e)}") from e

    async def get_context(
        self,
        session_id: UUID,
    ) -> ConversationContext:
        """Retrieve active conversation context delegating to conversation_manager.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            ConversationContext: Active conversation context entity.
        """
        self._require_initialized()
        try:
            return await self._conversation_manager.get_context(session_id=session_id)
        except ConversationError:
            raise
        except Exception as e:
            raise ConversationError(f"Failed to get context for session '{session_id}': {str(e)}") from e

    async def close_session(
        self,
        session_id: UUID,
    ) -> ConversationSession:
        """Close and archive a conversation session delegating to conversation_manager.

        Args:
            session_id: Unique session identifier UUID to close.

        Returns:
            ConversationSession: Closed conversation session entity.
        """
        self._require_initialized()
        try:
            return await self._conversation_manager.close_conversation(session_id=session_id)
        except ConversationError:
            raise
        except Exception as e:
            raise ConversationError(f"Failed to close conversation session '{session_id}': {str(e)}") from e

    async def health_check(self) -> ComponentHealth:
        """Check operational health of the conversation service.

        Returns:
            ComponentHealth: Operational component health status model.
        """
        if not self._initialized:
            return ComponentHealth(
                component_name="conversation_service",
                status=SystemHealthStatus.UNHEALTHY,
                message="ConversationService uninitialized.",
            )

        mgr_health = await self._conversation_manager.health_check()
        is_healthy = (
            isinstance(mgr_health, ComponentHealth)
            and mgr_health.status == SystemHealthStatus.HEALTHY
        )

        return ComponentHealth(
            component_name="conversation_service",
            status=SystemHealthStatus.HEALTHY if is_healthy else SystemHealthStatus.UNHEALTHY,
            message="ConversationService operational."
            if is_healthy
            else "ConversationService component degraded.",
        )
