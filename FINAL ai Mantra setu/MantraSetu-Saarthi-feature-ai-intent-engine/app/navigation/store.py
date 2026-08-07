"""In-memory storage layer for Navigation Intelligence in MantraSetu AgentOS.

This module implements NavigationStore, a thread-safe in-memory store for tracking WebsiteNode entities,
NavigationPlan instances, and NavigationContext states using asyncio primitives.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.base import (
    NavigationContextError,
    NavigationInitializationError,
)
from app.navigation.models import (
    NavigationContext,
    NavigationPlan,
    WebsiteNode,
)


class NavigationStore:
    """Thread-safe in-memory navigation entity storage manager.

    Responsibility:
        Provides thread-safe persistence and retrieval of WebsiteNode entities, NavigationPlan models,
        and NavigationContext states without external database dependencies.
    """

    def __init__(self) -> None:
        """Initialize NavigationStore with internal registries and asyncio lock."""
        self._nodes: dict[UUID, WebsiteNode] = {}
        self._plans: dict[UUID, NavigationPlan] = {}
        self._contexts: dict[UUID, NavigationContext] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the navigation store has been initialized.

        Raises:
            NavigationInitializationError: If initialize() has not been called.
        """
        if not self._initialized:
            raise NavigationInitializationError(
                "NavigationStore is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize navigation store runtime state. Idempotent."""
        async with self._lock:
            if self._initialized:
                return
            self._initialized = True

    async def close(self) -> None:
        """Close navigation store and clear all internal registries."""
        async with self._lock:
            self._nodes.clear()
            self._plans.clear()
            self._contexts.clear()
            self._initialized = False

    async def save_node(self, node: WebsiteNode) -> None:
        """Store a WebsiteNode entity.

        Args:
            node: WebsiteNode instance to store.

        Raises:
            NavigationInitializationError: If store is uninitialized.
            NavigationContextError: If node parameter is invalid.
        """
        self._require_initialized()
        if not isinstance(node, WebsiteNode):
            raise NavigationContextError("Invalid WebsiteNode instance provided.")

        async with self._lock:
            self._nodes[node.node_id] = node

    async def get_node(self, node_id: UUID) -> WebsiteNode:
        """Retrieve a WebsiteNode entity by identifier.

        Args:
            node_id: Unique node identifier UUID.

        Returns:
            WebsiteNode: Retrieved node entity.

        Raises:
            NavigationInitializationError: If store is uninitialized.
            NavigationContextError: If node_id is not found.
        """
        self._require_initialized()
        if not isinstance(node_id, UUID):
            raise NavigationContextError("Invalid node_id UUID provided.")

        async with self._lock:
            node = self._nodes.get(node_id)
            if not node:
                raise NavigationContextError(f"WebsiteNode '{node_id}' not found in store.")
            return node

    async def save_plan(self, plan: NavigationPlan) -> None:
        """Store a NavigationPlan model.

        Args:
            plan: NavigationPlan instance to store.

        Raises:
            NavigationInitializationError: If store is uninitialized.
            NavigationContextError: If plan parameter is invalid.
        """
        self._require_initialized()
        if not isinstance(plan, NavigationPlan):
            raise NavigationContextError("Invalid NavigationPlan instance provided.")

        async with self._lock:
            self._plans[plan.plan_id] = plan

    async def get_plan(self, plan_id: UUID) -> NavigationPlan:
        """Retrieve a NavigationPlan model by identifier.

        Args:
            plan_id: Unique plan identifier UUID.

        Returns:
            NavigationPlan: Retrieved navigation plan model.

        Raises:
            NavigationInitializationError: If store is uninitialized.
            NavigationContextError: If plan_id is not found.
        """
        self._require_initialized()
        if not isinstance(plan_id, UUID):
            raise NavigationContextError("Invalid plan_id UUID provided.")

        async with self._lock:
            plan = self._plans.get(plan_id)
            if not plan:
                raise NavigationContextError(f"NavigationPlan '{plan_id}' not found in store.")
            return plan

    async def save_context(self, context: NavigationContext) -> None:
        """Store a NavigationContext model keyed by session_id.

        Args:
            context: NavigationContext instance to store.

        Raises:
            NavigationInitializationError: If store is uninitialized.
            NavigationContextError: If context parameter or context.session_id is invalid.
        """
        self._require_initialized()
        if not isinstance(context, NavigationContext):
            raise NavigationContextError("Invalid NavigationContext instance provided.")
        if context.session_id is None:
            raise NavigationContextError("NavigationContext session_id cannot be None when storing context.")

        async with self._lock:
            self._contexts[context.session_id] = context

    async def get_context(self, session_id: UUID) -> NavigationContext:
        """Retrieve a NavigationContext model by session_id.

        Args:
            session_id: Unique user session identifier UUID.

        Returns:
            NavigationContext: Retrieved navigation context model.

        Raises:
            NavigationInitializationError: If store is uninitialized.
            NavigationContextError: If session_id is not found in store.
        """
        self._require_initialized()
        if not isinstance(session_id, UUID):
            raise NavigationContextError("Invalid session_id UUID provided.")

        async with self._lock:
            ctx = self._contexts.get(session_id)
            if not ctx:
                raise NavigationContextError(f"NavigationContext for session '{session_id}' not found in store.")
            return ctx

    async def health_check(self) -> ComponentHealth:
        """Check operational health of the navigation store.

        Returns:
            ComponentHealth: Operational component health status model.
        """
        return ComponentHealth(
            component_name="navigation_store",
            status=SystemHealthStatus.HEALTHY if self._initialized else SystemHealthStatus.UNHEALTHY,
            message="NavigationStore operational."
            if self._initialized
            else "NavigationStore uninitialized.",
        )
