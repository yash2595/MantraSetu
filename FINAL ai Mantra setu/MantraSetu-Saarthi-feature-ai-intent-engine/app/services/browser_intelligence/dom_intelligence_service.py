"""Default implementation of the DOM Intelligence Service abstraction."""

from __future__ import annotations

import logging
import time

from app.services.browser_intelligence.dom_intelligence_base import (
    DOMIntelligenceError,
    DOMIntelligenceService,
)
from app.services.browser_intelligence.dom_intelligence_models import (
    DOMIntelligence,
    SemanticCategory,
    SemanticElement,
)
from app.services.browser_intelligence.page_context_models import PageContext

logger = logging.getLogger(__name__)


class DefaultDOMIntelligenceService(DOMIntelligenceService):
    """Rule-based DOM Intelligence Service.

    Transforms raw PageContext into semantic DOM representations using
    simple heuristics without executing AI inference or browser interactions.
    """

    def __init__(self) -> None:
        """Initialize the DOM Intelligence Service."""
        pass

    def _is_primary_action(self, text: str) -> bool:
        """Determine if button text represents a primary action."""
        text_lower = text.lower()
        primary_keywords = ("book", "continue", "next", "proceed", "pay", "submit")
        return any(keyword in text_lower for keyword in primary_keywords)

    def _is_secondary_action(self, text: str) -> bool:
        """Determine if button text represents a secondary action."""
        text_lower = text.lower()
        secondary_keywords = ("cancel", "close", "back", "skip")
        return any(keyword in text_lower for keyword in secondary_keywords)

    async def analyze(self, context: PageContext) -> DOMIntelligence:
        """Analyze a raw PageContext and generate structured DOMIntelligence."""
        if context is None:
            raise DOMIntelligenceError("PageContext cannot be None.")

        logger.info("DOM analysis started")
        start_time = time.monotonic()

        primary_actions: list[SemanticElement] = []
        secondary_actions: list[SemanticElement] = []
        navigation_links: list[SemanticElement] = []
        input_fields: list[SemanticElement] = []

        # Analyze buttons
        for btn in context.buttons:
            if self._is_primary_action(btn.text):
                primary_actions.append(
                    SemanticElement(
                        text=btn.text,
                        selector=btn.selector,
                        category=SemanticCategory.PRIMARY_ACTION,
                        source="button",
                        visible=btn.visible,
                        enabled=btn.enabled,
                        confidence=1.0,
                    )
                )
            elif self._is_secondary_action(btn.text):
                secondary_actions.append(
                    SemanticElement(
                        text=btn.text,
                        selector=btn.selector,
                        category=SemanticCategory.SECONDARY_ACTION,
                        source="button",
                        visible=btn.visible,
                        enabled=btn.enabled,
                        confidence=1.0,
                    )
                )

        # Analyze navigation links
        for link in context.links:
            navigation_links.append(
                SemanticElement(
                    text=link.text,
                    selector=link.selector,
                    category=SemanticCategory.NAVIGATION,
                    source="link",
                    visible=link.visible,
                    enabled=link.enabled,
                    confidence=1.0,
                )
            )

        # Analyze input fields
        for inp in context.inputs:
            input_fields.append(
                SemanticElement(
                    text=inp.text,
                    selector=inp.selector,
                    category=SemanticCategory.INPUT,
                    source="input",
                    visible=inp.visible,
                    enabled=inp.enabled,
                    confidence=1.0,
                )
            )

        logger.info("Semantic classification completed")

        # Generate metadata
        metadata = {
            "button_count": len(context.buttons),
            "link_count": len(context.links),
            "input_count": len(context.inputs),
            "form_count": len(context.forms),
            "heading_count": len(context.headings),
            "primary_action_count": len(primary_actions),
            "secondary_action_count": len(secondary_actions),
            "has_navigation": len(navigation_links) > 0,
            "has_form": len(context.forms) > 0,
            "has_primary_action": len(primary_actions) > 0,
            "has_input": len(context.inputs) > 0,
        }
        logger.info("Metadata generated")

        try:
            intelligence = DOMIntelligence(
                primary_actions=primary_actions,
                secondary_actions=secondary_actions,
                navigation_links=navigation_links,
                input_fields=input_fields,
                metadata=metadata,
            )
        except ValueError as e:
            raise DOMIntelligenceError(f"Validation error generating intelligence: {e}") from e

        elapsed_ms = (time.monotonic() - start_time) * 1000
        logger.info("Processing time | processing_time_ms=%.2f", elapsed_ms)

        return intelligence
