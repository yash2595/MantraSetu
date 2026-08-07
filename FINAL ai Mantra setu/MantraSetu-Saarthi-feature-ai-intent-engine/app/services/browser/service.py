"""Concrete Browser Session implementation.

DefaultBrowserSession is a placeholder that satisfies the BrowserSession
interface. It enables the full pipeline to be wired up and tested before
the real browser automation engine (e.g. Playwright) is integrated.

Placeholder behaviour:
    - Returns implementation-neutral placeholder results for lifecycle operations.
    - Performs no browser launch, navigation, or automation.
"""

from __future__ import annotations

import logging
import time

from app.services.browser.base import BrowserSession, BrowserSessionError
from app.services.browser.models import BrowserSessionResult, BrowserState

logger = logging.getLogger(__name__)


class DefaultBrowserSession(BrowserSession):
    """Placeholder Browser Session.

    Returns implementation-neutral placeholder results without performing any real browser operations.
    Replace this with a concrete session (e.g. PlaywrightBrowserSession) inside the
    ServiceContainer when browser automation is ready.
    """

    async def start(self) -> BrowserSessionResult:
        """Return a placeholder 'stopped' result without launching a browser.

        Returns:
            BrowserSessionResult: Placeholder result for start operation. Never ``None``.
        """
        logger.info("Session start requested")
        t_start = time.monotonic()

        result = BrowserSessionResult(
            success=False,
            state=BrowserState.STOPPED,
            message="Placeholder browser session is not implemented.",
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info("Session start completed | processing_time_ms=%.2f", elapsed_ms)

        return result

    async def close(self) -> BrowserSessionResult:
        """Return a placeholder 'stopped' result without closing anything.

        Returns:
            BrowserSessionResult: Placeholder result for close operation. Never ``None``.
        """
        logger.info("Session close requested")
        t_start = time.monotonic()

        result = BrowserSessionResult(
            success=True,
            state=BrowserState.CLOSED,
            message="Placeholder browser session closed.",
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info("Session close completed | processing_time_ms=%.2f", elapsed_ms)

        return result

    async def state(self) -> BrowserSessionResult:
        """Return the current placeholder 'stopped' state.

        Returns:
            BrowserSessionResult: Placeholder result for state operation. Never ``None``.
        """
        logger.info("Session state requested")
        t_start = time.monotonic()

        result = BrowserSessionResult(
            success=True,
            state=BrowserState.STOPPED,
            message="Placeholder browser session is stopped.",
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info("Session state completed | processing_time_ms=%.2f", elapsed_ms)

        return result
