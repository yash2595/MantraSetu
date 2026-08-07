"""Booking Service package.

Public API:
    BookingService        — abstract base class (depend on this, not the concrete class).
    BookingServiceError   — only permitted error type (invalid input only).
    BookingType           — service category enum.
    BookingStatus         — booking lifecycle status enum.
    BookingRequest        — declarative booking details model.
    BookingResult         — immutable booking plan model.
    DefaultBookingService — placeholder concrete implementation.

Lifecycle:
    BookingService instances must be created and owned by the ServiceContainer.

Future backends:
    Replace DefaultBookingService with PlaywrightBookingService,
    BrowserAgentBookingService, etc. inside the ServiceContainer without
    changing any other module.
"""

from app.services.booking.base import BookingService, BookingServiceError
from app.services.booking.models import (
    BookingRequest,
    BookingResult,
    BookingStatus,
    BookingType,
)
from app.services.booking.service import DefaultBookingService

__all__ = [
    "BookingRequest",
    "BookingResult",
    "BookingService",
    "BookingServiceError",
    "BookingStatus",
    "BookingType",
    "DefaultBookingService",
]
