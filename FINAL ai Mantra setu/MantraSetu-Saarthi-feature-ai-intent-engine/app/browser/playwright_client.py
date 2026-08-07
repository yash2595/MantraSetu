"""Playwright browser automation client driver for MantraSetu AgentOS.

This module implements PlaywrightBrowserClient implementing BaseBrowserClient using Playwright's
async API for headless browser navigation, element interaction, and screenshot capture.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

try:
    from playwright.async_api import Browser, BrowserContext, Page, async_playwright
except ImportError:
    async_playwright = None  # type: ignore[assignment]
    Browser = None  # type: ignore[assignment, misc]
    BrowserContext = None  # type: ignore[assignment, misc]
    Page = None  # type: ignore[assignment, misc]

from app.browser.base import (
    BaseBrowserClient,
    BrowserExecutionError,
    BrowserInitializationError,
    BrowserNavigationError,
)
from app.browser.models import BrowserPage
from app.core.models import ComponentHealth, SystemHealthStatus


class PlaywrightBrowserClient(BaseBrowserClient):
    """Production-grade Playwright browser driver implementing BaseBrowserClient.

    Responsibility:
        Manages Playwright browser lifecycles, opens pages, clicks elements, fills form inputs,
        selects dropdown options, captures screenshots, and maps Playwright exceptions into domain errors.
    """

    def __init__(
        self,
        headless: bool = True,
        browser_type: str = "chromium",
        timeout_ms: float = 30000.0,
    ) -> None:
        """Initialize PlaywrightBrowserClient with options.

        Args:
            headless: Boolean flag for running browser in headless mode.
            browser_type: Playwright browser type string ("chromium", "firefox", "webkit").
            timeout_ms: Default action timeout in milliseconds.
        """
        self._headless = headless
        self._browser_type_name = browser_type
        self._timeout_ms = timeout_ms

        self._playwright: Any = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

        self._session_id = uuid4()
        self._initialized = False
        self._lock = asyncio.Lock()

    def _require_initialized(self) -> None:
        """Verify that the browser client has been initialized.

        Raises:
            BrowserInitializationError: If client is uninitialized.
        """
        if not self._initialized or self._page is None:
            raise BrowserInitializationError(
                "PlaywrightBrowserClient is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize Playwright driver and launch browser instance.

        Raises:
            BrowserInitializationError: If Playwright is not installed or launch fails.
        """
        if self._initialized:
            return

        if async_playwright is None:
            raise BrowserInitializationError(
                "The 'playwright' package is required for PlaywrightBrowserClient but is not installed."
            )

        async with self._lock:
            if self._initialized:
                return
            try:
                self._playwright = await async_playwright().start()
                launcher = getattr(self._playwright, self._browser_type_name, self._playwright.chromium)
                self._browser = await launcher.launch(headless=self._headless)
                self._context = await self._browser.new_context()
                self._page = await self._context.new_page()
                self._page.set_default_timeout(self._timeout_ms)
                self._initialized = True
            except Exception as e:
                await self.close()
                raise BrowserInitializationError(f"Failed to launch Playwright browser: {str(e)}") from e

    async def close(self) -> None:
        """Close browser instance, context, and Playwright driver resources."""
        async with self._lock:
            try:
                if self._page:
                    await self._page.close()
                if self._context:
                    await self._context.close()
                if self._browser:
                    await self._browser.close()
                if self._playwright:
                    await self._playwright.stop()
            except Exception:
                pass
            finally:
                self._page = None
                self._context = None
                self._browser = None
                self._playwright = None
                self._initialized = False

    async def open_page(self, url: str) -> BrowserPage:
        """Navigate browser to target URL and return loaded BrowserPage model.

        Args:
            url: Target URL string.

        Returns:
            BrowserPage: Loaded browser page domain model.

        Raises:
            BrowserInitializationError: If client is uninitialized.
            BrowserNavigationError: If page navigation fails.
        """
        self._require_initialized()
        assert self._page is not None

        try:
            response = await self._page.goto(url)
            page_url = self._page.url
            title = await self._page.title()
            content = await self._page.content()
            return BrowserPage(
                session_id=self._session_id,
                url=page_url or url,
                title=title or "",
                content=content or "",
            )
        except Exception as e:
            raise BrowserNavigationError(f"Failed to navigate to URL '{url}': {str(e)}") from e

    async def click(self, selector: str) -> None:
        """Click element matching target selector.

        Args:
            selector: CSS selector or element text identifier.

        Raises:
            BrowserInitializationError: If client is uninitialized.
            BrowserExecutionError: If element click fails.
        """
        self._require_initialized()
        assert self._page is not None

        try:
            await self._page.click(selector)
        except Exception as e:
            raise BrowserExecutionError(f"Failed to click element matching '{selector}': {str(e)}") from e

    async def fill(self, selector: str, value: str) -> None:
        """Fill input element matching selector with target value string.

        Args:
            selector: CSS selector or element input identifier.
            value: Text value string to input.

        Raises:
            BrowserInitializationError: If client is uninitialized.
            BrowserExecutionError: If input filling fails.
        """
        self._require_initialized()
        assert self._page is not None

        try:
            await self._page.fill(selector, value)
        except Exception as e:
            raise BrowserExecutionError(f"Failed to fill element '{selector}' with value: {str(e)}") from e

    async def select(self, selector: str, value: str) -> None:
        """Select option value in dropdown element matching selector.

        Args:
            selector: CSS selector or element select identifier.
            value: Option value string to select.

        Raises:
            BrowserInitializationError: If client is uninitialized.
            BrowserExecutionError: If dropdown selection fails.
        """
        self._require_initialized()
        assert self._page is not None

        try:
            await self._page.select_option(selector, value)
        except Exception as e:
            raise BrowserExecutionError(f"Failed to select option '{value}' in element '{selector}': {str(e)}") from e

    async def capture_screenshot(self, path: str | None = None) -> str:
        """Capture screenshot of the current page and return saved file path.

        Args:
            path: Optional target file path string.

        Returns:
            str: File path string of saved screenshot.

        Raises:
            BrowserInitializationError: If client is uninitialized.
            BrowserExecutionError: If screenshot capture fails.
        """
        self._require_initialized()
        assert self._page is not None

        target_path = path or f"screenshot_{self._session_id}.png"
        try:
            await self._page.screenshot(path=target_path)
            return target_path
        except Exception as e:
            raise BrowserExecutionError(f"Failed to capture screenshot: {str(e)}") from e

    async def get_current_page(self) -> BrowserPage | None:
        """Retrieve snapshot of the current active browser page.

        Returns:
            BrowserPage | None: Active page model if loaded, None otherwise.
        """
        if not self._initialized or self._page is None:
            return None

        try:
            return BrowserPage(
                session_id=self._session_id,
                url=self._page.url,
                title=await self._page.title(),
                content=await self._page.content(),
            )
        except Exception:
            return None

    async def health_check(self) -> ComponentHealth:
        """Check operational health of the Playwright browser client driver.

        Returns:
            ComponentHealth: Operational component health status model.
        """
        if not self._initialized or self._page is None:
            return ComponentHealth(
                component_name="playwright_client",
                status=SystemHealthStatus.UNHEALTHY,
                message="PlaywrightBrowserClient uninitialized.",
            )

        return ComponentHealth(
            component_name="playwright_client",
            status=SystemHealthStatus.HEALTHY,
            message="PlaywrightBrowserClient driver operational.",
        )
