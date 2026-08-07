"""Abstract base class and error types for the Navigation Service.

Defines the public interface that all concrete Navigation Service implementations
must satisfy. Consumers depend only on this contract — never on concrete classes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.orchestrator.models import UserRequest
from app.services.navigation.models import NavigationResult


class NavigationServiceError(Exception):
    """Raised when the Navigation Service receives invalid input it cannot process.

    This exception is raised only on malformed or missing input — never when
    navigation is simply not required. A 'not required' outcome always produces
    a valid ``NavigationResult`` with ``required=False``.
    """


class NavigationService(ABC):
    """Abstract interface for all Navigation Service implementations.

    Responsibility:
        Receive a ``UserRequest``, determine whether navigation is needed, and
        return a declarative ``NavigationResult`` describing the steps to
        perform. The service never executes browser automation, DOM parsing,
        or any HTTP requests itself.

    Contract:
        - Must be async.
        - Must never return ``None``.
        - Must never modify the incoming ``UserRequest``.
        - Must never call Playwright, Selenium, or any browser automation.
        - Raises ``NavigationServiceError`` only on invalid input.
        - Returns ``NavigationResult(required=False)`` when navigation is not
          needed.

    Future integrations (Playwright, BrowserService, DOM Parser, Vision Models,
    Computer Use Models, Multi-step Navigation, Dynamic UI Detection, Fallback
    Navigation, Recovery Strategy, Navigation Memory) can be wired into
    concrete subclasses without changing this interface.
    """

    @abstractmethod
    async def plan_navigation(self, request: UserRequest) -> NavigationResult:
        """Determine whether navigation is needed and build a declarative plan.

        Args:
            request: ``UserRequest`` domain model for the current user turn.
                     Planning uses ``request.user_input`` as the query.

        Returns:
            NavigationResult: Immutable navigation plan. Never ``None``.
            ``required=False`` is returned — not an exception — when navigation
            is not needed for the current request.

        Raises:
            NavigationServiceError: Only when ``request`` is invalid or
                                    ``user_input`` is missing / blank.
        """
        ...
