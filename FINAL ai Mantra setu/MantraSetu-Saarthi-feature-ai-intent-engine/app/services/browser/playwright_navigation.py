"""Concrete Playwright Navigation implementation.

PlaywrightNavigation is a concrete implementation of the BrowserNavigation
interface that uses the underlying BrowserDriver to execute navigation commands.

It does NOT handle Playwright APIs directly, does not manage lifecycle,
and does not interact with DOM elements.
"""

from __future__ import annotations

import logging
import time

from app.services.browser.driver_base import BrowserDriver
from app.services.browser.driver_models import DriverState
from app.services.browser.navigation_base import BrowserNavigation, BrowserNavigationError
from app.services.browser.navigation_models import BrowserNavigationResult, NavigationState
from app.services.browser.target_resolver_base import TargetResolver

logger = logging.getLogger(__name__)


class PlaywrightNavigation(BrowserNavigation):
    """Concrete Playwright Browser Navigation.

    Executes navigation commands (goto, back, forward, refresh, current_url)
    by delegating exclusively to the injected BrowserDriver.
    """

    def __init__(self, driver: BrowserDriver, target_resolver: TargetResolver) -> None:
        """Initialize with a BrowserDriver and TargetResolver.

        Args:
            driver: The low-level browser driver used to execute commands.
            target_resolver: Resolves logical targets to concrete URLs.
        """
        self._driver = driver
        self._target_resolver = target_resolver

    async def navigate(self, target: str) -> BrowserNavigationResult:
        """Navigate to a specified logical target using the driver.

        Args:
            target: The logical target to navigate to.

        Returns:
            BrowserNavigationResult: Immutable result of the navigation operation.
            Never ``None``.

        Raises:
            BrowserNavigationError: If ``target`` is None, empty, or whitespace.
        """
        if not target or not target.strip():
            raise BrowserNavigationError("target cannot be empty or whitespace.")

        logger.info("Navigation navigate requested | target=%s", target)
        t_start = time.monotonic()

        resolved_url = self._target_resolver.resolve_navigation_target(target)

        driver_result = await self._driver.execute("goto", url=resolved_url)

        nav_state = (
            NavigationState.COMPLETED if driver_result.state == DriverState.CONNECTED
            else NavigationState.IDLE if driver_result.state == DriverState.DISCONNECTED
            else NavigationState.FAILED
        )

        result = BrowserNavigationResult(
            success=driver_result.success,
            state=nav_state,
            message=driver_result.message,
            url=target,
            metadata=driver_result.metadata,
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Navigation navigate completed | state=%s | processing_time_ms=%.2f",
            result.state.value,
            elapsed_ms,
        )

        return result

    async def back(self) -> BrowserNavigationResult:
        """Navigate back in history using the driver.

        Returns:
            BrowserNavigationResult: Immutable result of the back operation.
            Never ``None``.
        """
        logger.info("Navigation back requested")
        t_start = time.monotonic()

        driver_result = await self._driver.execute("back")

        nav_state = (
            NavigationState.COMPLETED if driver_result.state == DriverState.CONNECTED
            else NavigationState.IDLE if driver_result.state == DriverState.DISCONNECTED
            else NavigationState.FAILED
        )

        result = BrowserNavigationResult(
            success=driver_result.success,
            state=nav_state,
            message=driver_result.message,
            metadata=driver_result.metadata,
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Navigation back completed | state=%s | processing_time_ms=%.2f",
            result.state.value,
            elapsed_ms,
        )

        return result

    async def forward(self) -> BrowserNavigationResult:
        """Navigate forward in history using the driver.

        Returns:
            BrowserNavigationResult: Immutable result of the forward operation.
            Never ``None``.
        """
        logger.info("Navigation forward requested")
        t_start = time.monotonic()

        driver_result = await self._driver.execute("forward")

        nav_state = (
            NavigationState.COMPLETED if driver_result.state == DriverState.CONNECTED
            else NavigationState.IDLE if driver_result.state == DriverState.DISCONNECTED
            else NavigationState.FAILED
        )

        result = BrowserNavigationResult(
            success=driver_result.success,
            state=nav_state,
            message=driver_result.message,
            metadata=driver_result.metadata,
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Navigation forward completed | state=%s | processing_time_ms=%.2f",
            result.state.value,
            elapsed_ms,
        )

        return result

    async def refresh(self) -> BrowserNavigationResult:
        """Refresh the current page using the driver.

        Returns:
            BrowserNavigationResult: Immutable result of the refresh operation.
            Never ``None``.
        """
        logger.info("Navigation refresh requested")
        t_start = time.monotonic()

        driver_result = await self._driver.execute("reload")

        nav_state = (
            NavigationState.COMPLETED if driver_result.state == DriverState.CONNECTED
            else NavigationState.IDLE if driver_result.state == DriverState.DISCONNECTED
            else NavigationState.FAILED
        )

        result = BrowserNavigationResult(
            success=driver_result.success,
            state=nav_state,
            message=driver_result.message,
            metadata=driver_result.metadata,
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Navigation refresh completed | state=%s | processing_time_ms=%.2f",
            result.state.value,
            elapsed_ms,
        )

        return result

    async def current_url(self) -> BrowserNavigationResult:
        """Get the current URL of the page using the driver.

        Returns:
            BrowserNavigationResult: Immutable result containing the URL.
            Never ``None``.
        """
        logger.info("Navigation current_url requested")
        t_start = time.monotonic()

        driver_result = await self._driver.execute("current_url")
        url = None
        if driver_result.success and driver_result.metadata:
            url = driver_result.metadata.get("url")

        nav_state = (
            NavigationState.COMPLETED if driver_result.state == DriverState.CONNECTED
            else NavigationState.IDLE if driver_result.state == DriverState.DISCONNECTED
            else NavigationState.FAILED
        )

        result = BrowserNavigationResult(
            success=driver_result.success,
            state=nav_state,
            message=driver_result.message,
            url=url,
            metadata=driver_result.metadata,
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Navigation current_url completed | state=%s | processing_time_ms=%.2f",
            result.state.value,
            elapsed_ms,
        )

        return result
