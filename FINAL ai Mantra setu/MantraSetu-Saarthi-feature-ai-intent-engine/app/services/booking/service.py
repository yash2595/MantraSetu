"""Concrete Booking Service implementation.

DefaultBookingService is a placeholder that satisfies the BookingService
interface and enables the full pipeline to be wired and tested end-to-end
before a real booking executor is connected.

Placeholder behaviour:
    - Always returns BookingResult(required=False, status=NOT_REQUIRED,
      booking_request=None, confirmation_id=None, message="", confidence=0.0).
    - Performs no browser automation, form submission, or HTTP requests.
    - Performs no Playwright, Selenium, or any UI interaction.
    - Performs no LLM calls.
    - Performs no payment, calendar, or availability operations.

Future replacement:
    Swap this class for a concrete implementation (e.g. PlaywrightBookingService,
    BrowserAgentBookingService) inside the ServiceContainer without changing the
    BookingService interface or any caller.
"""

from __future__ import annotations

import logging
import time

from app.orchestrator.models import UserRequest
from app.services.booking.base import BookingService, BookingServiceError
from app.services.booking.models import BookingResult, BookingStatus

logger = logging.getLogger(__name__)


class DefaultBookingService(BookingService):
    """Placeholder Booking Service that always returns a 'not required' result.

    This implementation satisfies the ``BookingService`` interface and allows
    the full request pipeline to be exercised end-to-end while the real
    booking executor (Playwright, payment gateway, calendar integration) is
    under development.

    Replace this class — inside the ``ServiceContainer`` only — with a real
    implementation when the executor is ready. No other module changes.
    """

    async def prepare_booking(self, request: UserRequest) -> BookingResult:
        """Return a placeholder 'not required' result without any booking preparation.

        Args:
            request: ``UserRequest`` domain model for the current user turn.

        Returns:
            BookingResult: Always ``required=False`` in this placeholder
            implementation. Never ``None``.

        Raises:
            BookingServiceError: If ``request`` is invalid or
                                 ``user_input`` is missing / blank.
        """
        if not isinstance(request, UserRequest):
            raise BookingServiceError(
                "request must be a UserRequest instance."
            )

        raw_input = request.user_input
        if not isinstance(raw_input, str) or not raw_input.strip():
            raise BookingServiceError(
                "request.user_input must be a non-empty string."
            )

        logger.info(
            "Booking preparation started | session_id=%s input_length=%d "
            "input_preview=%.80r",
            request.session_id,
            len(raw_input.strip()),
            raw_input.strip(),
        )

        t_start = time.monotonic()

        # Placeholder — no preparation performed
        result = BookingResult(
            required=False,
            status=BookingStatus.NOT_REQUIRED,
            booking_request=None,
            confirmation_id=None,
            message="",
            confidence=0.0,
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000

        logger.info(
            "Booking preparation completed | required=%s status=%s "
            "confidence=%.2f processing_time_ms=%.2f",
            result.required,
            result.status.value,
            result.confidence,
            elapsed_ms,
        )

        return result
