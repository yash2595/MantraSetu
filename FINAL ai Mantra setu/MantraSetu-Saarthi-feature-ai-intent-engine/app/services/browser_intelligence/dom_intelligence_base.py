"""Abstract base class and error types for DOM Intelligence Service."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.browser_intelligence.dom_intelligence_models import DOMIntelligence
from app.services.browser_intelligence.page_context_models import PageContext


class DOMIntelligenceError(Exception):
    """Raised when the DOM Intelligence Service encounters an error."""
    pass


class DOMIntelligenceService(ABC):
    """Abstract interface for analyzing and classifying PageContext semantically."""

    @abstractmethod
    async def analyze(self, context: PageContext) -> DOMIntelligence:
        """Convert a raw PageContext into structured DOMIntelligence.

        Args:
            context: The raw page context extracted from the browser.

        Returns:
            DOMIntelligence: The structured semantic DOM representation.

        Raises:
            DOMIntelligenceError: If analysis fails.
        """
        ...
