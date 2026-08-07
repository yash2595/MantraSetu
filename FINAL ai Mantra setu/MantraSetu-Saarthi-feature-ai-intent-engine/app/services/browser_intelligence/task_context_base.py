"""Abstract base class and error types for Task Context Builder."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.browser_intelligence.dom_intelligence_models import DOMIntelligence
from app.services.browser_intelligence.navigation_graph_models import NavigationGraph
from app.services.browser_intelligence.page_context_models import PageContext
from app.services.browser_intelligence.task_context_models import TaskContext


class TaskContextBuilderError(Exception):
    """Raised when the Task Context Builder encounters an error."""
    pass


class TaskContextBuilder(ABC):
    """Abstract interface for building a unified TaskContext."""

    @abstractmethod
    async def build(
        self,
        page_context: PageContext,
        dom_intelligence: DOMIntelligence,
        navigation_graph: NavigationGraph,
    ) -> TaskContext:
        """Compose multiple intelligence sources into a single TaskContext.

        Args:
            page_context: Extracted raw page information.
            dom_intelligence: Semantic DOM analysis.
            navigation_graph: Tracked navigation state.

        Returns:
            TaskContext: The unified context object.

        Raises:
            TaskContextBuilderError: If any input is None.
        """
        ...
