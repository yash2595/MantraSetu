"""Abstract base class and error types for the Browser Navigation abstraction.

Defines the high-level public interface for executing navigation in the browser.
Consumers depend only on this contract — never on concrete classes like
PlaywrightNavigation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.browser.navigation_models import BrowserNavigationResult


class BrowserNavigationError(Exception):
    """Raised when Browser Navigation is given invalid arguments.

    This exception is raised only on malformed arguments (e.g. empty url).
    It is never raised for execution failures (e.g. navigation timeout) which
    instead return a BrowserNavigationResult with success=False.
    """


class BrowserNavigation(ABC):
    """Abstract interface for all high-level Browser Navigation commands.

    Responsibility:
        Define standard high-level navigation (goto, back, forward, refresh)
        that uses the underlying BrowserDriver. This abstraction is not responsible
        for lifecycle management or DOM interaction.

    Contract:
        - Must be async.
        - Must never return ``None``.
        - Methods return ``BrowserNavigationResult``.
        - Raises ``BrowserNavigationError`` only on invalid arguments.
    """

    @abstractmethod
    async def navigate(self, target: str) -> BrowserNavigationResult:
        """Navigate to a specified logical target.

        Args:
            target: The logical target to navigate to.

        Returns:
            BrowserNavigationResult: Immutable result of the navigation operation.
            Never ``None``.

        Raises:
            BrowserNavigationError: If ``target`` is None, empty, or whitespace.
        """
        ...

    @abstractmethod
    async def back(self) -> BrowserNavigationResult:
        """Navigate back in history.

        Returns:
            BrowserNavigationResult: Immutable result of the back operation.
            Never ``None``.
        """
        ...

    @abstractmethod
    async def forward(self) -> BrowserNavigationResult:
        """Navigate forward in history.

        Returns:
            BrowserNavigationResult: Immutable result of the forward operation.
            Never ``None``.
        """
        ...

    @abstractmethod
    async def refresh(self) -> BrowserNavigationResult:
        """Refresh the current page.

        Returns:
            BrowserNavigationResult: Immutable result of the refresh operation.
            Never ``None``.
        """
        ...

    @abstractmethod
    async def current_url(self) -> BrowserNavigationResult:
        """Get the current URL of the page.

        Returns:
            BrowserNavigationResult: Immutable result containing the URL.
            Never ``None``.
        """
        ...
