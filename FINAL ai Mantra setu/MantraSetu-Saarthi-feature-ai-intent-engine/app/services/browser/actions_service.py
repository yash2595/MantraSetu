"""Concrete Browser Actions implementation.

DefaultBrowserActions is a placeholder that satisfies the BrowserActions
interface. It enables the full pipeline to be wired up and tested before
the real browser automation engine (e.g. Playwright) is integrated.

Placeholder behaviour:
    - Returns implementation-neutral placeholder results for all actions.
    - Performs no actual browser engine commands, scrolling, clicking, or typing.
"""

from __future__ import annotations

import logging
import time

from app.services.browser.actions_base import BrowserActionError, BrowserActions
from app.services.browser.actions_models import ActionState, BrowserActionResult
from app.services.browser.driver_base import BrowserDriver

logger = logging.getLogger(__name__)


class DefaultBrowserActions(BrowserActions):
    """Placeholder Browser Actions.

    Returns implementation-neutral placeholder results without performing any real actions.
    Constructor accepts a BrowserDriver instance which is stored but not used in this placeholder.
    """

    def __init__(self, driver: BrowserDriver) -> None:
        """Initialize the DefaultBrowserActions placeholder.

        Args:
            driver: The low-level browser driver. Stored but unused in this placeholder.
        """
        self.driver = driver

    async def click(self, selector: str) -> BrowserActionResult:
        """Return a placeholder result without clicking.

        Args:
            selector: The element selector to click.

        Returns:
            BrowserActionResult: Placeholder result for click action. Never ``None``.

        Raises:
            BrowserActionError: If ``selector`` is None, empty, or whitespace.
        """
        if not selector or not selector.strip():
            raise BrowserActionError("selector cannot be empty or whitespace.")

        logger.info("Action click requested")
        t_start = time.monotonic()

        result = BrowserActionResult(
            success=False,
            state=ActionState.IDLE,
            action="click",
            message="Placeholder click action is not implemented.",
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Action click completed | state=%s | processing_time_ms=%.2f",
            result.state.value,
            elapsed_ms,
        )

        return result

    async def type_text(self, selector: str, text: str) -> BrowserActionResult:
        """Return a placeholder result without typing text.

        Args:
            selector: The element selector to type into.
            text: The text to type (can be empty).

        Returns:
            BrowserActionResult: Placeholder result for type_text action. Never ``None``.

        Raises:
            BrowserActionError: If ``selector`` is invalid, or if ``text`` is None.
        """
        if not selector or not selector.strip():
            raise BrowserActionError("selector cannot be empty or whitespace.")
        if text is None:
            raise BrowserActionError("text cannot be None.")

        logger.info("Action type_text requested")
        t_start = time.monotonic()

        result = BrowserActionResult(
            success=False,
            state=ActionState.IDLE,
            action="type_text",
            message="Placeholder text input is not implemented.",
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Action type_text completed | state=%s | processing_time_ms=%.2f",
            result.state.value,
            elapsed_ms,
        )

        return result

    async def clear(self, selector: str) -> BrowserActionResult:
        """Return a placeholder result without clearing anything.

        Args:
            selector: The element selector to clear.

        Returns:
            BrowserActionResult: Placeholder result for clear action. Never ``None``.

        Raises:
            BrowserActionError: If ``selector`` is invalid.
        """
        if not selector or not selector.strip():
            raise BrowserActionError("selector cannot be empty or whitespace.")

        logger.info("Action clear requested")
        t_start = time.monotonic()

        result = BrowserActionResult(
            success=False,
            state=ActionState.IDLE,
            action="clear",
            message="Placeholder clear action is not implemented.",
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Action clear completed | state=%s | processing_time_ms=%.2f",
            result.state.value,
            elapsed_ms,
        )

        return result

    async def scroll(self, direction: str) -> BrowserActionResult:
        """Return a placeholder result without scrolling.

        Args:
            direction: The direction to scroll ('up', 'down', 'left', 'right').

        Returns:
            BrowserActionResult: Placeholder result for scroll action. Never ``None``.

        Raises:
            BrowserActionError: If ``direction`` is not one of the allowed values.
        """
        if direction not in ("up", "down", "left", "right"):
            raise BrowserActionError("direction must be one of: 'up', 'down', 'left', 'right'.")

        logger.info("Action scroll requested")
        t_start = time.monotonic()

        result = BrowserActionResult(
            success=False,
            state=ActionState.IDLE,
            action="scroll",
            message="Placeholder scroll action is not implemented.",
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Action scroll completed | state=%s | processing_time_ms=%.2f",
            result.state.value,
            elapsed_ms,
        )

        return result

    async def wait(self, seconds: float) -> BrowserActionResult:
        """Return a placeholder result without waiting.

        Args:
            seconds: The number of seconds to wait (>= 0).

        Returns:
            BrowserActionResult: Placeholder result for wait action. Never ``None``.

        Raises:
            BrowserActionError: If ``seconds`` is negative.
        """
        if seconds < 0:
            raise BrowserActionError("seconds cannot be negative.")

        logger.info("Action wait requested")
        t_start = time.monotonic()

        result = BrowserActionResult(
            success=False,
            state=ActionState.IDLE,
            action="wait",
            message="Placeholder wait action is not implemented.",
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Action wait completed | state=%s | processing_time_ms=%.2f",
            result.state.value,
            elapsed_ms,
        )

        return result
