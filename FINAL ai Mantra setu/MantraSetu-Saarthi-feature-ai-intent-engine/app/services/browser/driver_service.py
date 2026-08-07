"""Concrete Browser Driver implementation.

DefaultBrowserDriver is a placeholder that satisfies the BrowserDriver
interface. It enables the full pipeline to be wired up and tested before
the real browser automation engine (e.g. Playwright) is integrated.

Placeholder behaviour:
    - Returns implementation-neutral placeholder results for driver operations.
    - Performs no actual browser engine connections or commands.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from app.services.browser.driver_base import BrowserDriver, BrowserDriverError
from app.services.browser.driver_models import BrowserDriverResult, BrowserSessionHandle, DriverState

logger = logging.getLogger(__name__)


class DefaultBrowserDriver(BrowserDriver):
    """Placeholder Browser Driver.

    Returns implementation-neutral placeholder results without performing any real browser operations.
    Replace this with a concrete engine driver (e.g. PlaywrightBrowserDriver) inside the
    ServiceContainer when browser automation is ready.
    """

    async def connect(self) -> BrowserDriverResult:
        """Return a placeholder result without connecting to an engine.

        Returns:
            BrowserDriverResult: Placeholder result for connect operation. Never ``None``.
        """
        logger.info("Driver connect requested")
        t_start = time.monotonic()

        result = BrowserDriverResult(
            success=False,
            state=DriverState.DISCONNECTED,
            message="Placeholder browser driver is not implemented.",
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Driver connect completed | state=%s | processing_time_ms=%.2f",
            result.state.value,
            elapsed_ms,
        )

        return result

    async def disconnect(self) -> BrowserDriverResult:
        """Return a placeholder result without disconnecting anything.

        Returns:
            BrowserDriverResult: Placeholder result for disconnect operation. Never ``None``.
        """
        logger.info("Driver disconnect requested")
        t_start = time.monotonic()

        result = BrowserDriverResult(
            success=True,
            state=DriverState.DISCONNECTED,
            message="Placeholder browser driver disconnected.",
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Driver disconnect completed | state=%s | processing_time_ms=%.2f",
            result.state.value,
            elapsed_ms,
        )

        return result

    async def create_session(self, session_id: str) -> BrowserSessionHandle:
        """Return a placeholder session handle without creating real resources.

        Args:
            session_id: The unique identifier for the session.

        Returns:
            BrowserSessionHandle: A placeholder handle.
        """
        logger.info("Driver create_session requested | session_id=%s", session_id)
        return BrowserSessionHandle(session_id=session_id)

    async def close_session(self, session_id: str) -> BrowserDriverResult:
        """Return a placeholder result without closing real resources.

        Args:
            session_id: The unique identifier for the session.

        Returns:
            BrowserDriverResult: Placeholder result for close_session.
        """
        logger.info("Driver close_session requested | session_id=%s", session_id)
        return BrowserDriverResult(
            success=True,
            state=DriverState.DISCONNECTED,
            message="Placeholder session closed.",
        )

    async def execute(self, command: str, **kwargs: Any) -> BrowserDriverResult:
        """Return a placeholder result without executing any command.

        Args:
            command: The driver-specific command to execute.
            **kwargs: Additional parameters for the command.

        Returns:
            BrowserDriverResult: Placeholder result for execute operation. Never ``None``.

        Raises:
            BrowserDriverError: If ``command`` is empty or whitespace.
        """
        if not command or not command.strip():
            raise BrowserDriverError("Command string cannot be empty or whitespace.")

        logger.info("Driver execute requested | command=%s", command)
        t_start = time.monotonic()

        result = BrowserDriverResult(
            success=False,
            state=DriverState.DISCONNECTED,
            message="Placeholder browser driver cannot execute commands.",
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Driver execute completed | command=%s | state=%s | processing_time_ms=%.2f",
            command,
            result.state.value,
            elapsed_ms,
        )

        return result
