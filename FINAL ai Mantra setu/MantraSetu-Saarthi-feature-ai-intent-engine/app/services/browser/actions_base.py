"""Abstract base class and error types for the Browser Actions abstraction.

Defines the high-level public interface for executing actions in the browser.
Consumers depend only on this contract — never on concrete classes like
PlaywrightActions or BrowserlessActions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.browser.actions_models import BrowserActionResult


class BrowserActionError(Exception):
    """Raised when Browser Actions are given invalid arguments.

    This exception is raised only on malformed arguments (e.g. empty selector).
    It is never raised for execution failures (e.g. element not found) which
    instead return a BrowserActionResult with success=False.
    """


class BrowserActions(ABC):
    """Abstract interface for all high-level Browser Actions.

    Responsibility:
        Define standard high-level interactions (click, type, clear, scroll, wait)
        that use the underlying BrowserDriver. This abstraction is not responsible
        for lifecycle management or navigation.

    Contract:
        - Must be async.
        - Must never return ``None``.
        - Methods return ``BrowserActionResult``.
        - Raises ``BrowserActionError`` only on invalid arguments.
    """

    @abstractmethod
    async def click(self, target: str) -> BrowserActionResult:
        """Click an element matching the given logical target.

        Args:
            target: The logical element target to click.

        Returns:
            BrowserActionResult: Immutable result of the click operation.
            Never ``None``.

        Raises:
            BrowserActionError: If ``target`` is None, empty, or whitespace.
        """
        ...

    @abstractmethod
    async def type_text(self, target: str, value: str) -> BrowserActionResult:
        """Type value into an element matching the given logical target.

        Args:
            target: The logical element target to type into.
            value: The value to type (can be empty).

        Returns:
            BrowserActionResult: Immutable result of the type operation.
            Never ``None``.

        Raises:
            BrowserActionError: If ``target`` is invalid, or if ``value`` is None.
        """
        ...

    @abstractmethod
    async def clear(self, selector: str) -> BrowserActionResult:
        """Clear the value of an element matching the given selector.

        Args:
            selector: The element selector to clear.

        Returns:
            BrowserActionResult: Immutable result of the clear operation.
            Never ``None``.

        Raises:
            BrowserActionError: If ``selector`` is invalid.
        """
        ...

    @abstractmethod
    async def scroll(self, direction: str) -> BrowserActionResult:
        """Scroll the page in the specified direction.

        Args:
            direction: The direction to scroll ('up', 'down', 'left', 'right').

        Returns:
            BrowserActionResult: Immutable result of the scroll operation.
            Never ``None``.

        Raises:
            BrowserActionError: If ``direction`` is not one of the allowed values.
        """
        ...

    @abstractmethod
    async def wait(self, seconds: float) -> BrowserActionResult:
        """Wait for the specified number of seconds.

        Args:
            seconds: The number of seconds to wait (>= 0).

        Returns:
            BrowserActionResult: Immutable result of the wait operation.
            Never ``None``.

        Raises:
            BrowserActionError: If ``seconds`` is negative.
        """
        ...
