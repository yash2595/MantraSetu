"""Concrete Playwright Actions implementation.

PlaywrightActions is a concrete implementation of the BrowserActions
interface that uses the underlying BrowserDriver to execute action commands.

It does NOT handle Playwright APIs directly, does not manage lifecycle,
and does not interact with DOM elements natively.
"""

from __future__ import annotations

import logging
import time

from app.services.browser.actions_base import BrowserActionError, BrowserActions
from app.services.browser.actions_models import ActionState, BrowserActionResult
from app.services.browser.driver_base import BrowserDriver
from app.services.browser.driver_models import DriverState
from app.services.browser.target_resolver_base import TargetResolver

logger = logging.getLogger(__name__)


class PlaywrightActions(BrowserActions):
    """Concrete Playwright Browser Actions.

    Executes browser actions (click, type_text, clear, scroll, wait)
    by delegating exclusively to the injected BrowserDriver.
    """

    def __init__(self, driver: BrowserDriver, target_resolver: TargetResolver) -> None:
        """Initialize with a BrowserDriver and TargetResolver.

        Args:
            driver: The low-level browser driver used to execute commands.
            target_resolver: Resolves logical targets to concrete selectors.
        """
        self._driver = driver
        self._target_resolver = target_resolver

    async def click(self, target: str) -> BrowserActionResult:
        """Click an element matching the given logical target using the driver.

        Args:
            target: The logical element target to click.

        Returns:
            BrowserActionResult: Immutable result of the click operation.
            Never ``None``.

        Raises:
            BrowserActionError: If ``target`` is None, empty, or whitespace.
        """
        if not target or not target.strip():
            raise BrowserActionError("target cannot be empty or whitespace.")

        logger.info("Action click requested | target=%s", target)
        t_start = time.monotonic()

        selector = self._target_resolver.resolve_action_target(target)

        driver_result = await self._driver.execute("click", selector=selector)

        action_state = (
            ActionState.COMPLETED if driver_result.state == DriverState.CONNECTED
            else ActionState.IDLE if driver_result.state == DriverState.DISCONNECTED
            else ActionState.FAILED
        )

        result = BrowserActionResult(
            success=driver_result.success,
            state=action_state,
            action="click",
            message=driver_result.message,
            metadata=driver_result.metadata,
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Action click completed | state=%s | processing_time_ms=%.2f",
            result.state.value,
            elapsed_ms,
        )

        return result

    async def type_text(self, target: str, value: str) -> BrowserActionResult:
        """Type value into an element matching the given logical target using the driver.

        Args:
            target: The logical element target to type into.
            value: The value to type (can be empty).

        Returns:
            BrowserActionResult: Immutable result of the type operation.
            Never ``None``.

        Raises:
            BrowserActionError: If ``target`` is invalid, or if ``value`` is None.
        """
        if not target or not target.strip():
            raise BrowserActionError("target cannot be empty or whitespace.")
        if value is None:
            raise BrowserActionError("value cannot be None.")

        logger.info("Action type_text requested | target=%s", target)
        t_start = time.monotonic()

        selector = self._target_resolver.resolve_action_target(target)

        driver_result = await self._driver.execute("type_text", selector=selector, text=value)

        action_state = (
            ActionState.COMPLETED if driver_result.state == DriverState.CONNECTED
            else ActionState.IDLE if driver_result.state == DriverState.DISCONNECTED
            else ActionState.FAILED
        )

        result = BrowserActionResult(
            success=driver_result.success,
            state=action_state,
            action="type_text",
            message=driver_result.message,
            metadata=driver_result.metadata,
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Action type_text completed | state=%s | processing_time_ms=%.2f",
            result.state.value,
            elapsed_ms,
        )

        return result

    async def clear(self, selector: str) -> BrowserActionResult:
        """Clear the value of an element matching the given selector using the driver.

        Args:
            selector: The element selector to clear.

        Returns:
            BrowserActionResult: Immutable result of the clear operation.
            Never ``None``.

        Raises:
            BrowserActionError: If ``selector`` is invalid.
        """
        if not selector or not selector.strip():
            raise BrowserActionError("selector cannot be empty or whitespace.")

        logger.info("Action clear requested | selector=%s", selector)
        t_start = time.monotonic()

        # NOTE: If we migrate clear to use a logical target in the future, we would resolve it here.
        # selector = self._target_resolver.resolve_action_target(target)
        driver_result = await self._driver.execute("clear", selector=selector)

        action_state = (
            ActionState.COMPLETED if driver_result.state == DriverState.CONNECTED
            else ActionState.IDLE if driver_result.state == DriverState.DISCONNECTED
            else ActionState.FAILED
        )

        result = BrowserActionResult(
            success=driver_result.success,
            state=action_state,
            action="clear",
            message=driver_result.message,
            metadata=driver_result.metadata,
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Action clear completed | state=%s | processing_time_ms=%.2f",
            result.state.value,
            elapsed_ms,
        )

        return result

    async def scroll(self, direction: str) -> BrowserActionResult:
        """Scroll the page in the specified direction using the driver.

        Args:
            direction: The direction to scroll ('up', 'down', 'left', 'right').

        Returns:
            BrowserActionResult: Immutable result of the scroll operation.
            Never ``None``.

        Raises:
            BrowserActionError: If ``direction`` is not one of the allowed values.
        """
        if direction not in ("up", "down", "left", "right"):
            raise BrowserActionError("direction must be one of: 'up', 'down', 'left', 'right'.")

        logger.info("Action scroll requested | direction=%s", direction)
        t_start = time.monotonic()

        driver_result = await self._driver.execute("scroll", direction=direction)

        action_state = (
            ActionState.COMPLETED if driver_result.state == DriverState.CONNECTED
            else ActionState.IDLE if driver_result.state == DriverState.DISCONNECTED
            else ActionState.FAILED
        )

        result = BrowserActionResult(
            success=driver_result.success,
            state=action_state,
            action="scroll",
            message=driver_result.message,
            metadata=driver_result.metadata,
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Action scroll completed | state=%s | processing_time_ms=%.2f",
            result.state.value,
            elapsed_ms,
        )

        return result

    async def wait(self, seconds: float) -> BrowserActionResult:
        """Wait for the specified number of seconds using the driver.

        Args:
            seconds: The number of seconds to wait (>= 0).

        Returns:
            BrowserActionResult: Immutable result of the wait operation.
            Never ``None``.

        Raises:
            BrowserActionError: If ``seconds`` is negative.
        """
        if seconds < 0:
            raise BrowserActionError("seconds cannot be negative.")

        logger.info("Action wait requested | seconds=%.2f", seconds)
        t_start = time.monotonic()

        driver_result = await self._driver.execute("wait", seconds=seconds)

        action_state = (
            ActionState.COMPLETED if driver_result.state == DriverState.CONNECTED
            else ActionState.IDLE if driver_result.state == DriverState.DISCONNECTED
            else ActionState.FAILED
        )

        result = BrowserActionResult(
            success=driver_result.success,
            state=action_state,
            action="wait",
            message=driver_result.message,
            metadata=driver_result.metadata,
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Action wait completed | state=%s | processing_time_ms=%.2f",
            result.state.value,
            elapsed_ms,
        )

        return result
