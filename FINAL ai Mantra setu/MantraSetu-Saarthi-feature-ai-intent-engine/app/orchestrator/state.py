"""Orchestrator State Manager module for MantraSetu AgentOS.

This module implements OrchestratorStateManager for storing, retrieving, updating, and removing
immutable ExecutionContext instances in a thread-safe manner.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import UUID

from app.orchestrator.base import StateError
from app.orchestrator.models import ExecutionContext


def _utc_now() -> datetime:
    """Return the current timestamp in UTC.

    Returns:
        datetime: Current timezone-aware datetime instance in UTC.
    """
    return datetime.now(timezone.utc)


class OrchestratorStateManager:
    """Thread-safe runtime execution state manager.

    Responsibility:
        Manages registration, retrieval, atomic updating, and purging of immutable ExecutionContext
        instances associated with plan execution identifiers without executing plans or performing routing.
    """

    def __init__(self) -> None:
        """Initialize OrchestratorStateManager with internal registry and thread-safe lock."""
        self._contexts: dict[UUID, ExecutionContext] = {}
        self._lock = asyncio.Lock()

    async def store(self, context: ExecutionContext) -> None:
        """Register a new immutable ExecutionContext for a plan.

        Args:
            context: ExecutionContext model instance.

        Raises:
            StateError: If context is None, missing plan_id, or plan context already exists.
        """
        if not context:
            raise StateError("ExecutionContext cannot be None.")

        if not context.plan_id:
            raise StateError("ExecutionContext missing required plan_id.")

        async with self._lock:
            if context.plan_id in self._contexts:
                raise StateError(
                    f"Execution context for plan {context.plan_id} already exists."
                )
            self._contexts[context.plan_id] = context

    async def get(self, plan_id: UUID) -> ExecutionContext | None:
        """Retrieve an ExecutionContext by plan identifier.

        Args:
            plan_id: Unique plan identifier UUID.

        Returns:
            ExecutionContext | None: Context model if found, None otherwise.
        """
        async with self._lock:
            return self._contexts.get(plan_id)

    async def update(self, context: ExecutionContext) -> ExecutionContext:
        """Atomically replace an existing ExecutionContext for a plan.

        Args:
            context: Updated ExecutionContext model instance.

        Returns:
            ExecutionContext: Stored context model with updated timestamp.

        Raises:
            StateError: If context is None, missing plan_id, or plan context does not exist.
        """
        if not context:
            raise StateError("ExecutionContext cannot be None.")

        if not context.plan_id:
            raise StateError("ExecutionContext missing required plan_id.")

        async with self._lock:
            if context.plan_id not in self._contexts:
                raise StateError(
                    f"Execution context for plan {context.plan_id} not found."
                )

            updated = context.model_copy(update={"updated_at": _utc_now()})
            self._contexts[context.plan_id] = updated
            return updated

    async def remove(self, plan_id: UUID) -> None:
        """Remove an ExecutionContext from the registry by plan identifier.

        Args:
            plan_id: Unique plan identifier UUID.

        Raises:
            StateError: If plan context does not exist.
        """
        async with self._lock:
            if plan_id not in self._contexts:
                raise StateError(
                    f"Execution context for plan {plan_id} not found."
                )
            del self._contexts[plan_id]

    async def contains(self, plan_id: UUID) -> bool:
        """Check if an ExecutionContext is registered for a plan.

        Args:
            plan_id: Unique plan identifier UUID.

        Returns:
            bool: True if registered, False otherwise.
        """
        async with self._lock:
            return plan_id in self._contexts

    async def list_active(self) -> tuple[ExecutionContext, ...]:
        """List all active ExecutionContext instances.

        Returns:
            tuple[ExecutionContext, ...]: Immutable tuple of ExecutionContext models.
        """
        async with self._lock:
            return tuple(self._contexts.values())

    async def clear(self) -> None:
        """Clear all stored execution contexts from the registry."""
        async with self._lock:
            self._contexts.clear()
