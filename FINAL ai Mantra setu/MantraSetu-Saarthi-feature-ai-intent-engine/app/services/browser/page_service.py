"""Concrete Browser Page implementation.

DefaultBrowserPage is a placeholder that satisfies the BrowserPage
interface. It enables the full pipeline to be wired up and tested before
the real browser automation engine (e.g. Playwright) is integrated.

Placeholder behaviour:
    - Returns implementation-neutral placeholder results for lifecycle operations.
    - Performs no browser launch, tab creation, navigation, or automation.
"""

from __future__ import annotations

import logging
import time

from app.services.browser.page_base import BrowserPage
from app.services.browser.page_models import BrowserPageResult, PageState

logger = logging.getLogger(__name__)


class DefaultBrowserPage(BrowserPage):
    """Placeholder Browser Page.

    Returns implementation-neutral placeholder results without performing any real browser operations.
    Replace this with a concrete page (e.g. PlaywrightBrowserPage) inside the
    ServiceContainer when browser automation is ready.
    """

    async def create(self) -> BrowserPageResult:
        """Return a placeholder 'not created' result without launching a tab.

        Returns:
            BrowserPageResult: Placeholder result for create operation. Never ``None``.
        """
        logger.info("Page create requested")
        t_start = time.monotonic()

        result = BrowserPageResult(
            success=False,
            state=PageState.NOT_CREATED,
            url=None,
            title=None,
            message="Placeholder browser page is not implemented.",
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Page create completed | state=%s | processing_time_ms=%.2f",
            result.state.value,
            elapsed_ms,
        )

        return result

    async def close(self) -> BrowserPageResult:
        """Return a placeholder 'closed' result without closing anything.

        Returns:
            BrowserPageResult: Placeholder result for close operation. Never ``None``.
        """
        logger.info("Page close requested")
        t_start = time.monotonic()

        result = BrowserPageResult(
            success=True,
            state=PageState.CLOSED,
            url=None,
            title=None,
            message="Placeholder browser page closed.",
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Page close completed | state=%s | processing_time_ms=%.2f",
            result.state.value,
            elapsed_ms,
        )

        return result

    async def info(self) -> BrowserPageResult:
        """Return the current placeholder 'not created' info.

        Returns:
            BrowserPageResult: Placeholder result for info operation. Never ``None``.
        """
        logger.info("Page info requested")
        t_start = time.monotonic()

        result = BrowserPageResult(
            success=True,
            state=PageState.NOT_CREATED,
            url=None,
            title=None,
            message="Placeholder browser page is not created.",
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Page info completed | state=%s | processing_time_ms=%.2f",
            result.state.value,
            elapsed_ms,
        )

        return result
