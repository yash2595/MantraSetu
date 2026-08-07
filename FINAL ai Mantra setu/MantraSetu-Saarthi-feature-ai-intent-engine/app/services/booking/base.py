"""Abstract base class and error types for the Booking Service.

Defines the public interface that all concrete Booking Service implementations
must satisfy. Consumers depend only on this contract — never on concrete classes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.orchestrator.models import UserRequest
from app.services.booking.models import BookingResult


class BookingServiceError(Exception):
    """Raised when the Booking Service receives invalid input it cannot process.

    This exception is raised only on malformed or missing input — never when
    booking is simply not required. A 'not required' outcome always produces
    a valid ``BookingResult`` with ``required=False``.
    """


class BookingService(ABC):
    """Abstract interface for all Booking Service implementations.

    Responsibility:
        Receive a ``UserRequest``, determine whether a booking is needed, and
        return a declarative ``BookingResult`` describing the booking to
        prepare. The service never submits forms, calls payment gateways,
        or performs browser automation itself.

    Contract:
        - Must be async.
        - Must never return ``None``.
        - Must never modify the incoming ``UserRequest``.
        - Must never call Playwright, Selenium, or any browser automation.
        - Must never execute payment or calendar operations.
        - Raises ``BookingServiceError`` only on invalid input.
        - Returns ``BookingResult(required=False)`` when booking is not needed.

    Future integrations (Playwright, BrowserService, Payment Gateway, Calendar
    Integration, Availability Checking, Booking Confirmation, Rescheduling,
    Cancellation, Reminder Service) can be wired into concrete subclasses
    without changing this interface.
    """

    @abstractmethod
    async def prepare_booking(self, request: UserRequest) -> BookingResult:
        """Determine whether a booking is needed and build a declarative plan.

        Args:
            request: ``UserRequest`` domain model for the current user turn.
                     Preparation uses ``request.user_input`` as the query.

        Returns:
            BookingResult: Immutable booking plan. Never ``None``.
            ``required=False`` is returned — not an exception — when booking
            is not needed for the current request.

        Raises:
            BookingServiceError: Only when ``request`` is invalid or
                                 ``user_input`` is missing / blank.
        """
        ...
