"""Concrete Browser Context implementation.

DefaultBrowserContext is a placeholder that satisfies the BrowserContext
interface. It enables the full pipeline to be wired up and tested before
the real browser automation engine (e.g. Playwright) is integrated.

Placeholder behaviour:
    - Returns implementation-neutral placeholder results for lifecycle operations.
    - Performs no browser launch, context creation, navigation, or automation.
"""

from __future__ import annotations

import logging
import time

from app.services.browser.context_base import BrowserContext
from app.services.browser.context_models import BrowserContextResult, ContextState

logger = logging.getLogger(__name__)


class DefaultBrowserContext(BrowserContext):
    """Placeholder Browser Context.

    Returns implementation-neutral placeholder results without performing any real browser operations.
    Replace this with a concrete context (e.g. PlaywrightBrowserContext) inside the
    ServiceContainer when browser automation is ready.
    """

    async def create(self) -> BrowserContextResult:
        """Return a placeholder 'not created' result without creating a context.

        Returns:
            BrowserContextResult: Placeholder result for create operation. Never ``None``.
        """
        logger.info("Context create requested")
        t_start = time.monotonic()

        result = BrowserContextResult(
            success=False,
            state=ContextState.NOT_CREATED,
            context_id=None,
            message="Placeholder browser context is not implemented.",
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Context create completed | state=%s | processing_time_ms=%.2f",
            result.state.value,
            elapsed_ms,
        )

        return result

    async def close(self) -> BrowserContextResult:
        """Return a placeholder 'closed' result without closing anything.

        Returns:
            BrowserContextResult: Placeholder result for close operation. Never ``None``.
        """
        logger.info("Context close requested")
        t_start = time.monotonic()

        result = BrowserContextResult(
            success=True,
            state=ContextState.CLOSED,
            context_id=None,
            message="Placeholder browser context closed.",
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Context close completed | state=%s | processing_time_ms=%.2f",
            result.state.value,
            elapsed_ms,
        )

        return result

    async def info(self) -> BrowserContextResult:
        """Return the current placeholder 'not created' info.

        Returns:
            BrowserContextResult: Placeholder result for info operation. Never ``None``.
        """
        logger.info("Context info requested")
        t_start = time.monotonic()

        result = BrowserContextResult(
            success=True,
            state=ContextState.NOT_CREATED,
            context_id=None,
            message="Placeholder browser context is not created.",
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Context info completed | state=%s | processing_time_ms=%.2f",
            result.state.value,
            elapsed_ms,
        )

        return result
