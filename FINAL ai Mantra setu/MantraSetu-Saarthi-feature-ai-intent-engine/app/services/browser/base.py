"""Abstract base class and error types for the Browser Session abstraction.

Defines the public interface that all concrete Browser Session implementations
must satisfy. Consumers depend only on this contract — never on concrete classes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.browser.models import BrowserSessionResult


class BrowserSessionError(Exception):
    """Raised when the Browser Session is given invalid arguments or usage.

    This exception is raised only on malformed usage — never for standard
    lifecycle failures (e.g. failing to start due to timeout). Lifecycle
    failures return a BrowserSessionResult with success=False.
    """


class BrowserSession(ABC):
    """Abstract interface for all Browser Session implementations.

    Responsibility:
        Manage the lifecycle of a browser instance (start, close, state).
        This abstraction is not responsible for browser automation, DOM interaction,
        navigation, Playwright specifics, clicking, or filling forms.

    Contract:
        - Must be async.
        - Must never return ``None``.
        - Methods return ``BrowserSessionResult``.
        - Raises ``BrowserSessionError`` only on invalid arguments.

    Future integrations (Playwright, Persistent Context, Incognito Context,
    Multiple Browser Instances, Authentication, Cookies, Downloads, Uploads,
    Tracing, DevTools) can be wired into concrete subclasses without changing
    this interface.
    """

    @abstractmethod
    async def start(self) -> BrowserSessionResult:
        """Start the browser session.

        Returns:
            BrowserSessionResult: Immutable result of the start operation.
            Never ``None``.
        """
        ...

    @abstractmethod
    async def close(self) -> BrowserSessionResult:
        """Close the browser session and release resources.

        Returns:
            BrowserSessionResult: Immutable result of the close operation.
            Never ``None``.
        """
        ...

    @abstractmethod
    async def state(self) -> BrowserSessionResult:
        """Get the current state of the browser session.

        Returns:
            BrowserSessionResult: Immutable result containing the current state.
            Never ``None``.
        """
        ...
