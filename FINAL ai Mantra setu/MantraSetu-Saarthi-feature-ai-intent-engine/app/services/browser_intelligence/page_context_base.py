"""Abstract base class and error types for the Page Context Extractor."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.browser_intelligence.page_context_models import PageContext


class PageContextExtractorError(Exception):
    """Raised when the Page Context Extractor encounters an error."""
    pass


class PageContextExtractor(ABC):
    """Abstract interface for extracting context from a browser page."""

    @abstractmethod
    async def extract(self) -> PageContext:
        """Extract the current page context.

        Returns:
            PageContext: The structured page context.

        Raises:
            PageContextExtractorError: If extraction fails.
        """
        ...
