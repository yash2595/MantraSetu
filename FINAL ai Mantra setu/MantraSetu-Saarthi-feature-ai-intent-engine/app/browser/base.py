"""Abstract contracts and interfaces for the Browser Automation subsystem in MantraSetu AgentOS.

This module defines abstract base classes for browser automation clients and action executors
alongside domain exception hierarchies for browser management.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.browser.models import (
    BrowserActionResult,
    BrowserPage,
)
from app.core.models import ComponentHealth
from app.navigation.models import NavigationAction


class BrowserError(Exception):
    """Base exception for all browser automation subsystem errors."""

    pass


class BrowserSessionError(BrowserError):
    """Raised when browser session creation or management fails."""

    pass


class BrowserNavigationError(BrowserError):
    """Raised when page opening or URL navigation fails."""

    pass


class BrowserExecutionError(BrowserError):
    """Raised when element interaction or action execution fails."""

    pass


class BrowserInitializationError(BrowserError):
    """Raised when browser client component initialization fails."""

    pass


class BaseBrowserClient(ABC):
    """Abstract interface defining the contract for browser automation drivers."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize browser driver and launch browser instance."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close browser instance, context, and driver connections."""
        ...

    @abstractmethod
    async def open_page(self, url: str) -> BrowserPage:
        """Navigate browser to target URL and return page snapshot model.

        Args:
            url: Target URL string.

        Returns:
            BrowserPage: Loaded browser page domain model.

        Raises:
            BrowserNavigationError: If page navigation fails.
        """
        ...

    @abstractmethod
    async def click(self, selector: str) -> None:
        """Click element matching target CSS selector or text description.

        Args:
            selector: CSS selector or element text identifier.

        Raises:
            BrowserExecutionError: If element click fails.
        """
        ...

    @abstractmethod
    async def fill(self, selector: str, value: str) -> None:
        """Fill input element matching selector with target text value.

        Args:
            selector: CSS selector or element input identifier.
            value: Text value string to input.

        Raises:
            BrowserExecutionError: If input filling fails.
        """
        ...

    @abstractmethod
    async def select(self, selector: str, value: str) -> None:
        """Select option value in dropdown element matching selector.

        Args:
            selector: CSS selector or element select identifier.
            value: Option value string to select.

        Raises:
            BrowserExecutionError: If dropdown selection fails.
        """
        ...

    @abstractmethod
    async def capture_screenshot(self, path: str | None = None) -> str:
        """Capture screenshot of the current page and return file path.

        Args:
            path: Optional target file path string.

        Returns:
            str: Absolute file path string of saved screenshot.

        Raises:
            BrowserExecutionError: If screenshot capture fails.
        """
        ...

    @abstractmethod
    async def get_current_page(self) -> BrowserPage | None:
        """Retrieve snapshot of the current active browser page.

        Returns:
            BrowserPage | None: Active page model if loaded, None otherwise.
        """
        ...

    @abstractmethod
    async def health_check(self) -> ComponentHealth:
        """Perform an operational health check on the browser client driver.

        Returns:
            ComponentHealth: Operational component health status model.
        """
        ...


class BaseBrowserExecutor(ABC):
    """Abstract interface defining the contract for browser action execution engines."""

    @abstractmethod
    async def execute(
        self,
        action: NavigationAction,
    ) -> BrowserActionResult:
        """Execute a NavigationAction command through browser client driver.

        Args:
            action: NavigationAction model command.

        Returns:
            BrowserActionResult: Action execution outcome result model.

        Raises:
            BrowserExecutionError: If action mapping or execution fails.
        """
        ...
