"""Default implementation of the Page Context Extractor abstraction."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from app.services.browser.page_base import BrowserPage, BrowserPageError
from app.services.browser_intelligence.page_context_base import (
    PageContextExtractor,
    PageContextExtractorError,
)
from app.services.browser_intelligence.page_context_models import (
    PageContext,
    PageElement,
)

logger = logging.getLogger(__name__)


class DefaultPageContextExtractor(PageContextExtractor):
    """Extracts structured PageContext from a BrowserPage without side effects.

    This service is strictly READ-ONLY. It utilizes only the BrowserPage
    abstraction and performs zero DOM modifications or AI reasoning.
    """

    def __init__(self, browser_page: BrowserPage) -> None:
        """Initialize with a BrowserPage dependency.

        Args:
            browser_page: The browser page abstraction to extract data from.
        """
        self._browser_page = browser_page

    def _parse_elements(self, raw_elements: list[dict[str, Any]] | None) -> list[PageElement]:
        """Parse raw dictionary elements into PageElement objects."""
        if not raw_elements:
            return []
        
        parsed = []
        for el in raw_elements:
            if isinstance(el, dict):
                parsed.append(
                    PageElement(
                        text=el.get("text", ""),
                        selector=el.get("selector", ""),
                        visible=bool(el.get("visible", False)),
                        enabled=bool(el.get("enabled", False)),
                    )
                )
        return parsed

    async def extract(self) -> PageContext:
        """Extract the current page context."""
        logger.info("Page analysis started")
        start_time = time.monotonic()

        try:
            info_result = await self._browser_page.info()
        except BrowserPageError as e:
            raise PageContextExtractorError(f"Failed to extract context: {e}") from e

        if not info_result.success:
            raise PageContextExtractorError(
                f"Page information retrieval failed: {info_result.message}"
            )

        url = info_result.url or ""
        title = info_result.title or ""

        logger.info("URL extracted | url=%s", url)

        # Assuming the metadata contains DOM elements extracted by the underlying driver
        metadata = info_result.metadata or {}

        buttons = self._parse_elements(metadata.get("buttons", []))
        inputs = self._parse_elements(metadata.get("inputs", []))
        links = self._parse_elements(metadata.get("links", []))
        forms = metadata.get("forms", [])
        headings = metadata.get("headings", [])
        language = metadata.get("language")

        logger.info(
            "DOM elements extracted | buttons=%d | inputs=%d | links=%d | forms=%d | headings=%d",
            len(buttons),
            len(inputs),
            len(links),
            len(forms),
            len(headings),
        )

        try:
            context = PageContext(
                url=url,
                title=title,
                buttons=buttons,
                inputs=inputs,
                links=links,
                forms=forms,
                headings=headings,
                language=language,
                captured_at=datetime.now(timezone.utc),
            )
        except ValueError as e:
            raise PageContextExtractorError(f"Validation error: {e}") from e

        logger.info("PageContext generated")
        
        elapsed_ms = (time.monotonic() - start_time) * 1000
        logger.info("Processing time | processing_time_ms=%.2f", elapsed_ms)

        return context
