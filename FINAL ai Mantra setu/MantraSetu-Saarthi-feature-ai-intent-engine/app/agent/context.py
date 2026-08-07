"""Agent Context Service orchestration layer for MantraSetu AgentOS.

This module implements AgentContextService, providing thread-safe in-memory creation,
retrieval, updating, and deletion of AgentContext models for active agent task executions.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

from app.agent.base import (
    AgentContextError,
    AgentInitializationError,
)
from app.agent.models import AgentContext
from app.core.models import ComponentHealth, SystemHealthStatus


class AgentContextService:
    """Service providing thread-safe in-memory AgentContext lifecycle management.

    Responsibility:
        Creates, retrieves, updates, and deletes AgentContext models keyed by task_id
        without external database or LLM SDK dependencies.
    """

    def __init__(self) -> None:
        """Initialize AgentContextService with internal context registry and asyncio lock."""
        self._contexts: dict[UUID, AgentContext] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the context service has been initialized.

        Raises:
            AgentInitializationError: If initialize() has not been called.
        """
        if not self._initialized:
            raise AgentInitializationError(
                "AgentContextService is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize context service runtime state. Idempotent."""
        async with self._lock:
            if self._initialized:
                return
            self._initialized = True

    async def close(self) -> None:
        """Close context service and purge all stored AgentContext entries."""
        async with self._lock:
            self._contexts.clear()
            self._initialized = False

    async def create_context(
        self,
        task_id: UUID,
        conversation_id: UUID | None = None,
        session_id: UUID | None = None,
    ) -> AgentContext:
        """Create and store a new AgentContext for the given task_id.

        Args:
            task_id: Associated AgentTask identifier UUID.
            conversation_id: Optional associated conversation identifier UUID.
            session_id: Optional associated user session identifier UUID.

        Returns:
            AgentContext: Newly created agent context model.

        Raises:
            AgentInitializationError: If service is uninitialized.
            AgentContextError: If task_id is invalid.
        """
        self._require_initialized()
        if not isinstance(task_id, UUID):
            raise AgentContextError("Invalid task_id UUID provided.")

        context = AgentContext(
            task_id=task_id,
            conversation_id=conversation_id,
            session_id=session_id,
        )
        async with self._lock:
            self._contexts[task_id] = context
        return context

    async def get_context(self, task_id: UUID) -> AgentContext:
        """Retrieve an active AgentContext by task_id.

        Args:
            task_id: Associated AgentTask identifier UUID.

        Returns:
            AgentContext: Retrieved agent context model.

        Raises:
            AgentInitializationError: If service is uninitialized.
            AgentContextError: If task_id is not found.
        """
        self._require_initialized()
        if not isinstance(task_id, UUID):
            raise AgentContextError("Invalid task_id UUID provided.")

        async with self._lock:
            context = self._contexts.get(task_id)
            if context is None:
                raise AgentContextError(
                    f"AgentContext for task '{task_id}' not found."
                )
            return context

    async def update_context(self, context: AgentContext) -> AgentContext:
        """Update an existing AgentContext model in the registry.

        Args:
            context: Updated AgentContext instance to store.

        Returns:
            AgentContext: Updated agent context model.

        Raises:
            AgentInitializationError: If service is uninitialized.
            AgentContextError: If context is invalid or task_id is not found.
        """
        self._require_initialized()
        if not isinstance(context, AgentContext):
            raise AgentContextError("Invalid AgentContext instance provided.")

        async with self._lock:
            if context.task_id not in self._contexts:
                raise AgentContextError(
                    f"AgentContext for task '{context.task_id}' not found."
                )
            self._contexts[context.task_id] = context
        return context

    async def delete_context(self, task_id: UUID) -> None:
        """Delete an AgentContext entry by task_id.

        Args:
            task_id: Associated AgentTask identifier UUID.

        Raises:
            AgentInitializationError: If service is uninitialized.
            AgentContextError: If task_id is not found.
        """
        self._require_initialized()
        if not isinstance(task_id, UUID):
            raise AgentContextError("Invalid task_id UUID provided.")

        async with self._lock:
            if task_id not in self._contexts:
                raise AgentContextError(
                    f"AgentContext for task '{task_id}' not found."
                )
            del self._contexts[task_id]

    async def health_check(self) -> ComponentHealth:
        """Check operational health of the agent context service.

        Returns:
            ComponentHealth: Operational component health status model.
        """
        return ComponentHealth(
            component_name="agent_context_service",
            status=SystemHealthStatus.HEALTHY if self._initialized else SystemHealthStatus.UNHEALTHY,
            message="AgentContextService operational."
            if self._initialized
            else "AgentContextService uninitialized.",
        )
