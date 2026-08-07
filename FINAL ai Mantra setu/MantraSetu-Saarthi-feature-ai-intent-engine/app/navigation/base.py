"""Abstract contracts and interfaces for the Navigation Intelligence subsystem in MantraSetu AgentOS.

This module defines abstract base classes for navigation planners, website graphs, site analyzers,
and action execution engines alongside domain exception hierarchies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.navigation.models import (
    NavigationAction,
    NavigationContext,
    NavigationEdge,
    NavigationPlan,
    WebsiteNode,
)


class NavigationError(Exception):
    """Base exception for all navigation subsystem errors."""

    pass


class NavigationGraphError(NavigationError):
    """Raised when website structure graph node or edge operations fail."""

    pass


class NavigationPlanningError(NavigationError):
    """Raised when navigation goal plan generation fails."""

    pass


class NavigationExecutionError(NavigationError):
    """Raised when browser action execution fails."""

    pass


class NavigationContextError(NavigationError):
    """Raised when navigation context or history updates fail."""

    pass


class NavigationInitializationError(NavigationError):
    """Raised when a navigation component initialization fails."""

    pass


class BaseNavigationPlanner(ABC):
    """Abstract interface defining the contract for goal-oriented navigation planners."""

    @abstractmethod
    async def create_plan(
        self,
        goal: str,
        context: NavigationContext,
    ) -> NavigationPlan:
        """Generate a multi-step NavigationPlan to achieve a user goal.

        Args:
            goal: Human-readable goal description string.
            context: Active NavigationContext configuration.

        Returns:
            NavigationPlan: Created navigation plan model.

        Raises:
            NavigationPlanningError: If plan creation fails.
        """
        ...


class BaseNavigationGraph(ABC):
    """Abstract interface defining the contract for website structure map stores."""

    @abstractmethod
    async def add_node(
        self,
        node: WebsiteNode,
    ) -> None:
        """Add a WebsiteNode entity to the navigation graph.

        Args:
            node: WebsiteNode instance to register.

        Raises:
            NavigationGraphError: If node insertion fails.
        """
        ...

    @abstractmethod
    async def add_edge(
        self,
        edge: NavigationEdge,
    ) -> None:
        """Add a NavigationEdge transition connecting two nodes in the graph.

        Args:
            edge: NavigationEdge instance to register.

        Raises:
            NavigationGraphError: If edge insertion fails.
        """
        ...

    @abstractmethod
    async def find_path(
        self,
        source: UUID,
        target: UUID,
    ) -> tuple[WebsiteNode, ...]:
        """Find optimal path sequence of WebsiteNode entities between source and target nodes.

        Args:
            source: Source node identifier UUID.
            target: Target node identifier UUID.

        Returns:
            tuple[WebsiteNode, ...]: Immutable tuple of ordered WebsiteNode entities.

        Raises:
            NavigationGraphError: If no valid path exists or query fails.
        """
        ...


class BaseNavigationAnalyzer(ABC):
    """Abstract interface defining the contract for website structure analyzers."""

    @abstractmethod
    async def analyze(
        self,
        url: str,
    ) -> tuple[WebsiteNode, ...]:
        """Analyze a web page URL and discover navigation nodes.

        Args:
            url: Page URL string to analyze.

        Returns:
            tuple[WebsiteNode, ...]: Immutable tuple of discovered WebsiteNode entities.

        Raises:
            NavigationError: If page analysis fails.
        """
        ...


class BaseNavigationExecutor(ABC):
    """Abstract interface defining the contract for navigation action execution engines."""

    @abstractmethod
    async def execute(
        self,
        action: NavigationAction,
    ) -> bool:
        """Execute an individual NavigationAction command.

        Args:
            action: NavigationAction model command.

        Returns:
            bool: True if execution succeeded, False otherwise.

        Raises:
            NavigationExecutionError: If action execution fails.
        """
        ...
