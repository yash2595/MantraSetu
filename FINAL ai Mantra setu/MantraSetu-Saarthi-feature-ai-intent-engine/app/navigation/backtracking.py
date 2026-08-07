"""Navigation Backtracking Service orchestration layer for MantraSetu AgentOS.

This module implements BacktrackingService for maintaining thread-safe navigation context history,
detecting failed navigation steps, and popping back to previous valid navigation contexts.
"""

from __future__ import annotations

import asyncio

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.base import (
    NavigationContextError,
    NavigationInitializationError,
)
from app.navigation.models import NavigationContext


class BacktrackingService:
    """Service facade managing navigation context history stacks and state recovery.

    Responsibility:
        Maintains an in-memory stack of NavigationContext snapshots, allowing the system to record
        valid navigation checkpoints and backtrack to previous contexts upon step failures.
    """

    def __init__(self) -> None:
        """Initialize BacktrackingService with internal context stack and asyncio lock."""
        self._history: list[NavigationContext] = []
        self._lock = asyncio.Lock()
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the backtracking service has been initialized.

        Raises:
            NavigationInitializationError: If initialize() has not been called.
        """
        if not self._initialized:
            raise NavigationInitializationError(
                "BacktrackingService is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize backtracking service runtime state. Idempotent."""
        async with self._lock:
            if self._initialized:
                return
            self._initialized = True

    async def close(self) -> None:
        """Close backtracking service and clear recorded context history stack."""
        async with self._lock:
            self._history.clear()
            self._initialized = False

    async def push_state(
        self,
        context: NavigationContext,
    ) -> None:
        """Push a valid NavigationContext snapshot onto the history stack.

        Args:
            context: NavigationContext model snapshot to record.

        Raises:
            NavigationInitializationError: If service is uninitialized.
            NavigationContextError: If context parameter is invalid.
        """
        self._require_initialized()
        if not isinstance(context, NavigationContext):
            raise NavigationContextError("Invalid NavigationContext instance provided.")

        async with self._lock:
            self._history.append(context)

    async def backtrack(self) -> NavigationContext:
        """Pop current failed state and return the previous valid NavigationContext snapshot.

        Returns:
            NavigationContext: Previous valid navigation context model.

        Raises:
            NavigationInitializationError: If service is uninitialized.
            NavigationContextError: If no previous context exists to backtrack to.
        """
        self._require_initialized()
        async with self._lock:
            if not self._history:
                raise NavigationContextError(
                    "No navigation context available to backtrack."
                )

            # Pop current state
            self._history.pop()

            if not self._history:
                raise NavigationContextError(
                    "No previous navigation context available to backtrack."
                )

            return self._history[-1]

    async def get_history(self) -> tuple[NavigationContext, ...]:
        """Retrieve complete chronological stack of recorded NavigationContext snapshots.

        Returns:
            tuple[NavigationContext, ...]: Immutable tuple of recorded NavigationContext objects.

        Raises:
            NavigationInitializationError: If service is uninitialized.
        """
        self._require_initialized()
        async with self._lock:
            return tuple(self._history)

    async def health_check(self) -> ComponentHealth:
        """Check operational health of the backtracking service.

        Returns:
            ComponentHealth: Operational component health status model.
        """
        return ComponentHealth(
            component_name="backtracking_service",
            status=SystemHealthStatus.HEALTHY if self._initialized else SystemHealthStatus.UNHEALTHY,
            message="BacktrackingService operational."
            if self._initialized
            else "BacktrackingService uninitialized.",
        )
