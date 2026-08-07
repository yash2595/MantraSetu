"""Default implementation of the Task Context Builder abstraction."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.services.browser_intelligence.dom_intelligence_models import DOMIntelligence
from app.services.browser_intelligence.navigation_graph_models import NavigationGraph
from app.services.browser_intelligence.page_context_models import PageContext
from app.services.browser_intelligence.task_context_base import (
    TaskContextBuilder,
    TaskContextBuilderError,
)
from app.services.browser_intelligence.task_context_models import (
    TaskContext,
    TaskSummary,
)

logger = logging.getLogger(__name__)


class DefaultTaskContextBuilder(TaskContextBuilder):
    """Purely compositional builder for creating unified TaskContexts.

    Does not alter inputs, execute logic, or hold state.
    """

    async def build(
        self,
        page_context: PageContext,
        dom_intelligence: DOMIntelligence,
        navigation_graph: NavigationGraph,
    ) -> TaskContext:
        """Compose inputs into a single TaskContext."""
        logger.info("TaskContext creation started")

        if page_context is None:
            raise TaskContextBuilderError("page_context cannot be None.")
        if dom_intelligence is None:
            raise TaskContextBuilderError("dom_intelligence cannot be None.")
        if navigation_graph is None:
            raise TaskContextBuilderError("navigation_graph cannot be None.")

        logger.info("Validation completed")

        navigation_link_count = 0
        if page_context.url in navigation_graph.nodes:
            navigation_link_count = len(navigation_graph.nodes[page_context.url].links)

        try:
            summary = TaskSummary(
                page_url=page_context.url,
                page_title=page_context.title,
                primary_action_count=len(dom_intelligence.primary_actions),
                secondary_action_count=len(dom_intelligence.secondary_actions),
                navigation_link_count=navigation_link_count,
                input_field_count=len(dom_intelligence.input_fields),
                has_navigation=dom_intelligence.metadata.get("has_navigation", False),
                has_form=dom_intelligence.metadata.get("has_form", False),
                has_primary_action=dom_intelligence.metadata.get("has_primary_action", False),
                has_input=dom_intelligence.metadata.get("has_input", False),
            )
            logger.info("TaskSummary generated")

            task_context = TaskContext(
                summary=summary,
                page_context=page_context,
                dom_intelligence=dom_intelligence,
                navigation_graph=navigation_graph,
                created_at=datetime.now(timezone.utc),
            )
        except ValueError as e:
            raise TaskContextBuilderError(f"Validation error building TaskContext: {e}") from e

        logger.info("TaskContext created successfully")
        return task_context
