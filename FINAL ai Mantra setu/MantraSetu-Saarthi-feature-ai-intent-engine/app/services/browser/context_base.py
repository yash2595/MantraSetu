"""Abstract base class and error types for the Browser Context abstraction.

Defines the public interface that all concrete Browser Context implementations
must satisfy. Consumers depend only on this contract — never on concrete classes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.browser.context_models import BrowserContextResult


class BrowserContextError(Exception):
    """Raised when the Browser Context is given invalid arguments or usage.

    This exception is raised only on malformed usage — never for standard
    lifecycle failures (e.g. failing to create due to timeout). Lifecycle
    failures return a BrowserContextResult with success=False.
    """


class BrowserContext(ABC):
    """Abstract interface for all Browser Context implementations.

    Responsibility:
        Manage the lifecycle of an isolated browser context (create, close, info).
        This abstraction is not responsible for launching the browser, page
        creation, navigation, or DOM interaction.

    Contract:
        - Must be async.
        - Must never return ``None``.
        - Methods return ``BrowserContextResult``.
        - Raises ``BrowserContextError`` only on invalid arguments.

    Future integrations (PlaywrightBrowserContext, Persistent contexts,
    Incognito contexts, Multiple browser contexts, Cookie management,
    Storage state, Authentication, Permissions, Tracing, Downloads,
    Uploads) can be wired into concrete subclasses without changing this interface.
    """

    @abstractmethod
    async def create(self) -> BrowserContextResult:
        """Prepare an isolated browser context.

        Returns:
            BrowserContextResult: Immutable result of the create operation.
            Never ``None``.
        """
        ...

    @abstractmethod
    async def close(self) -> BrowserContextResult:
        """Close the browser context.

        Returns:
            BrowserContextResult: Immutable result of the close operation.
            Never ``None``.
        """
        ...

    @abstractmethod
    async def info(self) -> BrowserContextResult:
        """Get information about the current context state.

        Returns:
            BrowserContextResult: Immutable result containing the context info.
            Never ``None``.
        """
        ...
