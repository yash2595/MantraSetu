"""Orchestrator Context Store for MantraSetu AgentOS.

This module implements OrchestratorStore, a thread-safe in-memory storage manager
for OrchestratorContext models keyed by request_id, following the SessionStore and NavigationStore patterns.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

from app.core.models import ComponentHealth, SystemHealthStatus
from app.orchestrator.base import (
    OrchestratorInitializationError,
    OrchestratorStoreError,
)
from app.orchestrator.models import OrchestratorContext


class OrchestratorStore:
    """Thread-safe in-memory OrchestratorContext storage manager.

    Responsibility:
        Provides thread-safe persistence, retrieval, and deletion of OrchestratorContext
        models keyed by request_id without external database dependencies.
    """

    def __init__(self) -> None:
        """Initialize OrchestratorStore with internal context registry and asyncio lock."""
        self._contexts: dict[UUID, OrchestratorContext] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the orchestrator store has been initialized.

        Raises:
            OrchestratorInitializationError: If initialize() has not been called.
        """
        if not self._initialized:
            raise OrchestratorInitializationError(
                "OrchestratorStore is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize orchestrator store runtime state. Idempotent."""
        async with self._lock:
            if self._initialized:
                return
            self._initialized = True

    async def close(self) -> None:
        """Close orchestrator store and purge all stored context entries."""
        async with self._lock:
            self._contexts.clear()
            self._initialized = False

    async def save(self, context: OrchestratorContext) -> None:
        """Persist an OrchestratorContext model keyed by request_id.

        Args:
            context: OrchestratorContext model to store.

        Raises:
            OrchestratorInitializationError: If store is uninitialized.
            OrchestratorStoreError: If context parameter is invalid.
        """
        self._require_initialized()
        if not isinstance(context, OrchestratorContext):
            raise OrchestratorStoreError("Invalid OrchestratorContext instance provided.")

        async with self._lock:
            self._contexts[context.request_id] = context

    async def get(self, request_id: UUID) -> OrchestratorContext:
        """Retrieve an OrchestratorContext by request_id.

        Args:
            request_id: Associated UserRequest identifier UUID.

        Returns:
            OrchestratorContext: Retrieved orchestrator context model.

        Raises:
            OrchestratorInitializationError: If store is uninitialized.
            OrchestratorStoreError: If request_id is not found.
        """
        self._require_initialized()
        if not isinstance(request_id, UUID):
            raise OrchestratorStoreError("Invalid request_id UUID provided.")

        async with self._lock:
            context = self._contexts.get(request_id)
            if context is None:
                raise OrchestratorStoreError(
                    f"OrchestratorContext for request '{request_id}' not found."
                )
            return context

    async def delete(self, request_id: UUID) -> None:
        """Delete an OrchestratorContext entry by request_id.

        Args:
            request_id: Associated UserRequest identifier UUID to remove.

        Raises:
            OrchestratorInitializationError: If store is uninitialized.
            OrchestratorStoreError: If request_id is not found.
        """
        self._require_initialized()
        if not isinstance(request_id, UUID):
            raise OrchestratorStoreError("Invalid request_id UUID provided.")

        async with self._lock:
            if request_id not in self._contexts:
                raise OrchestratorStoreError(
                    f"OrchestratorContext for request '{request_id}' not found."
                )
            del self._contexts[request_id]

    async def exists(self, request_id: UUID) -> bool:
        """Check whether an OrchestratorContext exists for a given request_id.

        Args:
            request_id: Associated UserRequest identifier UUID.

        Returns:
            bool: True if context exists, False otherwise.

        Raises:
            OrchestratorInitializationError: If store is uninitialized.
        """
        self._require_initialized()
        async with self._lock:
            return request_id in self._contexts

    async def health_check(self) -> ComponentHealth:
        """Check operational health of the orchestrator store.

        Returns:
            ComponentHealth: Operational component health status model.
        """
        return ComponentHealth(
            component_name="orchestrator_store",
            status=SystemHealthStatus.HEALTHY if self._initialized else SystemHealthStatus.UNHEALTHY,
            message="OrchestratorStore operational."
            if self._initialized
            else "OrchestratorStore uninitialized.",
        )
