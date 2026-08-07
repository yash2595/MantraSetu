"""Abstract base class and error types for the Browser Page abstraction.

Defines the public interface that all concrete Browser Page implementations
must satisfy. Consumers depend only on this contract — never on concrete classes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.browser.page_models import BrowserPageResult


class BrowserPageError(Exception):
    """Raised when the Browser Page is given invalid arguments or usage.

    This exception is raised only on malformed usage — never for standard
    lifecycle failures (e.g. failing to create due to timeout). Lifecycle
    failures return a BrowserPageResult with success=False.
    """


class BrowserPage(ABC):
    """Abstract interface for all Browser Page implementations.

    Responsibility:
        Manage the lifecycle of a browser page (create, close, info).
        This abstraction represents a single tab or context, but is not
        responsible for launching the browser or DOM interaction (clicking, typing).

    Contract:
        - Must be async.
        - Must never return ``None``.
        - Methods return ``BrowserPageResult``.
        - Raises ``BrowserPageError`` only on invalid arguments.

    Future integrations (PlaywrightBrowserPage, Multiple tabs, Popup windows,
    Browser events, Network monitoring, Authentication, Downloads, Uploads,
    Tracing, Persistent browser contexts, Incognito contexts) can be wired
    into concrete subclasses without changing this interface.
    """

    @abstractmethod
    async def create(self) -> BrowserPageResult:
        """Prepare a browser page. Concrete implementations define how the page is created.

        Returns:
            BrowserPageResult: Immutable result of the create operation.
            Never ``None``.
        """
        ...

    @abstractmethod
    async def close(self) -> BrowserPageResult:
        """Close the browser page.

        Returns:
            BrowserPageResult: Immutable result of the close operation.
            Never ``None``.
        """
        ...

    @abstractmethod
    async def info(self) -> BrowserPageResult:
        """Get information about the current page (URL, title, state).

        Returns:
            BrowserPageResult: Immutable result containing the page info.
            Never ``None``.
        """
        ...
