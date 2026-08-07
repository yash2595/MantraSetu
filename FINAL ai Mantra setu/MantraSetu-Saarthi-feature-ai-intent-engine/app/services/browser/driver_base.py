"""Abstract base class and error types for the Browser Driver abstraction.

Defines the low-level public interface that all concrete Browser Driver engines
must satisfy. Consumers (like Navigation, Locator layers) depend only on this
contract — never on concrete classes like PlaywrightBrowserDriver.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.services.browser.driver_models import BrowserDriverResult, BrowserSessionHandle


class BrowserDriverError(Exception):
    """Raised when the Browser Driver is given invalid arguments or usage.

    This exception is raised only on malformed usage (e.g. empty command string).
    It is never raised for standard engine execution failures (e.g. timeout,
    element not found) which instead return a BrowserDriverResult with success=False.
    """


class BrowserDriver(ABC):
    """Abstract interface for all low-level Browser Driver engines.

    Responsibility:
        Provide a bridge between higher-level browser abstractions and the actual
        underlying browser engine (e.g. Playwright, Selenium, CDP).
        This abstraction executes raw commands. It is not responsible for business
        logic.
        
    Ownership Model:
        - The Driver creates and owns the single Browser instance.
        - The Driver creates and owns multiple Browser Contexts.
        - The Driver creates and owns One Page per Session.
        - The Driver maps session_id to BrowserSessionHandle internally.

    Contract:
        - Must be async.
        - Must never return ``None``.
        - Methods return ``BrowserDriverResult``.
        - Raises ``BrowserDriverError`` only on invalid arguments.
    """

    @abstractmethod
    async def connect(self) -> BrowserDriverResult:
        """Connect to the browser engine.

        Returns:
            BrowserDriverResult: Immutable result of the connect operation.
            Never ``None``.
        """
        ...

    @abstractmethod
    async def disconnect(self) -> BrowserDriverResult:
        """Disconnect from the browser engine.

        Returns:
            BrowserDriverResult: Immutable result of the disconnect operation.
            Never ``None``.
        """
        ...

    @abstractmethod
    async def create_session(self, session_id: str) -> BrowserSessionHandle:
        """Create a new browser session (context and page) for the given session ID.

        Args:
            session_id: The unique identifier for the session.

        Returns:
            BrowserSessionHandle: The internal handle containing Playwright objects.
        """
        ...

    @abstractmethod
    async def close_session(self, session_id: str) -> BrowserDriverResult:
        """Close and release all browser resources associated with the session ID.

        Args:
            session_id: The unique identifier for the session.

        Returns:
            BrowserDriverResult: Immutable result of the close operation.
        """
        ...

    @abstractmethod
    async def execute(self, command: str, **kwargs: Any) -> BrowserDriverResult:
        """Execute a low-level command on the browser engine.

        Args:
            command: The driver-specific command to execute (e.g. 'click', 'goto').
            **kwargs: Additional parameters for the command.

        Returns:
            BrowserDriverResult: Immutable result of the execute operation.
            Never ``None``.

        Raises:
            BrowserDriverError: If ``command`` is empty or whitespace.
        """
        ...
