"""Concrete Playwright Browser Driver implementation.

PlaywrightBrowserDriver is a concrete implementation of the BrowserDriver
interface that uses Playwright's async API to manage the browser engine.
It handles low-level browser connection and basic engine commands.

It does NOT handle high-level navigation abstractions, DOM interactions,
or business logic.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from app.services.browser.driver_base import BrowserDriver, BrowserDriverError
from app.services.browser.driver_models import BrowserDriverResult, BrowserSessionHandle, DriverState

logger = logging.getLogger(__name__)


class PlaywrightBrowserDriver(BrowserDriver):
    """Concrete Playwright Browser Driver.

    Manages the lifecycle of a Chromium browser instance via Playwright.
    Executes low-level browser commands (goto, reload, back, forward).
    """

    def __init__(self) -> None:
        """Initialize the driver with empty private state."""
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._sessions: dict[str, BrowserSessionHandle] = {}

    async def connect(self) -> BrowserDriverResult:
        """Start Playwright and launch a Chromium browser instance.

        Returns:
            BrowserDriverResult: Immutable result of the connect operation.
            Never ``None``.
        """
        logger.info("Driver connect requested")
        t_start = time.monotonic()

        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch()

            result = BrowserDriverResult(
                success=True,
                state=DriverState.CONNECTED,
                message="Browser driver connected.",
            )
        except Exception as e:
            # Clean up partial state if startup failed
            await self.disconnect()
            result = BrowserDriverResult(
                success=False,
                state=DriverState.FAILED,
                message=f"Failed to connect Playwright: {str(e)}",
            )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Driver connect completed | state=%s | processing_time_ms=%.2f",
            result.state.value,
            elapsed_ms,
        )

        return result

    async def disconnect(self) -> BrowserDriverResult:
        """Safely disconnect and close all Playwright resources.

        This method is safe to call multiple times.

        Returns:
            BrowserDriverResult: Immutable result of the disconnect operation.
            Never ``None``.
        """
        logger.info("Driver disconnect requested")
        t_start = time.monotonic()

        try:
            for handle in list(self._sessions.values()):
                if handle.browser_page:
                    await handle.browser_page.close()
                if handle.browser_context:
                    await handle.browser_context.close()
            self._sessions.clear()

            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.warning("Error during Playwright disconnect: %s", e)
        finally:
            self._browser = None
            self._playwright = None

        result = BrowserDriverResult(
            success=True,
            state=DriverState.DISCONNECTED,
            message="Browser driver disconnected.",
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Driver disconnect completed | state=%s | processing_time_ms=%.2f",
            result.state.value,
            elapsed_ms,
        )

        return result

    async def create_session(self, session_id: str) -> BrowserSessionHandle:
        """Create a new browser session context and page for the given session ID."""
        if not self._browser:
            raise BrowserDriverError("Cannot create session: Browser is not connected.")
            
        context = await self._browser.new_context()
        page = await context.new_page()
        
        handle = BrowserSessionHandle(
            session_id=session_id,
            browser=self._browser,
            browser_context=context,
            browser_page=page,
        )
        self._sessions[session_id] = handle
        return handle

    async def close_session(self, session_id: str) -> BrowserDriverResult:
        """Close resources for a specific session."""
        handle = self._sessions.pop(session_id, None)
        if not handle:
            return BrowserDriverResult(
                success=False,
                state=DriverState.CONNECTED,
                message=f"Session {session_id} not found."
            )
            
        try:
            if handle.browser_page:
                await handle.browser_page.close()
            if handle.browser_context:
                await handle.browser_context.close()
                
            return BrowserDriverResult(
                success=True,
                state=DriverState.CONNECTED,
                message=f"Session {session_id} closed."
            )
        except Exception as e:
            return BrowserDriverResult(
                success=False,
                state=DriverState.CONNECTED,
                message=f"Failed to close session {session_id}: {str(e)}"
            )

    async def execute(self, command: str, **kwargs: Any) -> BrowserDriverResult:
        """Execute a low-level command on the browser engine.

        Supported commands:
            - goto (requires 'url' kwarg)
            - reload
            - back
            - forward
            - current_url

        Args:
            command: The driver-specific command to execute.
            **kwargs: Additional parameters for the command.

        Returns:
            BrowserDriverResult: Immutable result of the execute operation.
            Never ``None``.

        Raises:
            BrowserDriverError: If ``command`` is empty or whitespace.
        """
        if not command or not command.strip():
            raise BrowserDriverError("Command string cannot be empty or whitespace.")

        if not self._browser:
            return BrowserDriverResult(
                success=False,
                state=DriverState.DISCONNECTED,
                message="Cannot execute command. Driver is disconnected.",
            )

        # NOTE: For a real multi-session engine, execute() should accept session_id.
        # This implementation simply takes the first active session as a fallback placeholder.
        active_handle = next(iter(self._sessions.values()), None)
        if not active_handle or not active_handle.browser_page:
            return BrowserDriverResult(
                success=False,
                state=DriverState.CONNECTED,
                message="Cannot execute command. No active session page.",
            )
            
        page = active_handle.browser_page

        command = command.strip().lower()
        logger.info("Driver execute requested | command=%s", command)
        t_start = time.monotonic()

        result: BrowserDriverResult

        try:
            if command == "goto":
                url = kwargs.get("url")
                if not url:
                    return BrowserDriverResult(
                        success=False,
                        state=DriverState.CONNECTED,
                        message="Missing required 'url' argument for 'goto' command.",
                    )
                await page.goto(str(url))
                result = BrowserDriverResult(
                    success=True,
                    state=DriverState.CONNECTED,
                    message=f"Navigated to {url}",
                )

            elif command == "reload":
                await page.reload()
                result = BrowserDriverResult(
                    success=True,
                    state=DriverState.CONNECTED,
                    message="Page reloaded.",
                )

            elif command == "back":
                await page.go_back()
                result = BrowserDriverResult(
                    success=True,
                    state=DriverState.CONNECTED,
                    message="Navigated back.",
                )

            elif command == "forward":
                await page.go_forward()
                result = BrowserDriverResult(
                    success=True,
                    state=DriverState.CONNECTED,
                    message="Navigated forward.",
                )

            elif command == "current_url":
                current = page.url
                result = BrowserDriverResult(
                    success=True,
                    state=DriverState.CONNECTED,
                    message="Retrieved current URL.",
                    metadata={"url": current},
                )

            else:
                result = BrowserDriverResult(
                    success=False,
                    state=DriverState.FAILED,
                    message="Unsupported driver command.",
                )

        except Exception as e:
            result = BrowserDriverResult(
                success=False,
                state=DriverState.FAILED,
                message=f"Playwright execution failed: {str(e)}",
            )

        elapsed_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Driver execute completed | command=%s | state=%s | processing_time_ms=%.2f",
            command,
            result.state.value,
            elapsed_ms,
        )

        return result
