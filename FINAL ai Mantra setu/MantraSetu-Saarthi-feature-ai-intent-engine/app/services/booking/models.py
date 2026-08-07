"""Domain models for the Booking Service.

These Pydantic v2 models define the data contract for booking preparation.
They are intentionally free of any browser, form-submission, or payment logic
so the Booking Service can evolve — connecting Playwright, payment gateways,
calendar integrations — without changing the public interface.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import Field

from app.schemas.base import SchemaModel


# ---------------------------------------------------------------------------
# Booking type enumeration
# ---------------------------------------------------------------------------


class BookingType(str, Enum):
    """Classifies the category of service being booked.

    Values:
        UNKNOWN:        Booking type has not been determined.
        PUJA:           A ritual / puja booking at home or temple.
        PANDIT:         A pandit / priest booking for a ceremony.
        TEMPLE_VISIT:   A scheduled visit to a specific temple.
        CONSULTATION:   A spiritual or astrological consultation booking.
    """

    UNKNOWN = "unknown"
    PUJA = "puja"
    PANDIT = "pandit"
    TEMPLE_VISIT = "temple_visit"
    CONSULTATION = "consultation"


# ---------------------------------------------------------------------------
# Booking status enumeration
# ---------------------------------------------------------------------------


class BookingStatus(str, Enum):
    """Lifecycle status of a booking request or operation.

    Values:
        NOT_REQUIRED: Booking is not needed for this request.
        PENDING:      A booking plan has been created but not submitted.
        IN_PROGRESS:  Booking submission is currently being processed.
        COMPLETED:    Booking was submitted and confirmed successfully.
        FAILED:       Booking submission was attempted and failed.
    """

    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Booking request model
# ---------------------------------------------------------------------------


class BookingRequest(SchemaModel):
    """Describes the details of a service booking to be prepared.

    This model is declarative — it describes *what* to book, not *how* to
    execute the booking. The actual submission happens in the browser agent layer.

    Attributes:
        booking_type:    Category of service being booked.
        service_name:    Name of the specific service or puja (e.g. "Rudrabhishek").
        preferred_date:  User's preferred booking date as a free-form string.
        preferred_time:  User's preferred time slot as a free-form string.
        location:        Location preference (city, temple name, or "home").
        user_details:    Optional user-provided details (name, phone, address).
        metadata:        Optional free-form context forwarded to the executor.
    """

    booking_type: BookingType = Field(
        default=BookingType.UNKNOWN,
        description="Category of service being booked.",
    )
    service_name: str = Field(
        default="",
        description="Name of the specific service or puja.",
    )
    preferred_date: Optional[str] = Field(
        default=None,
        description="User's preferred booking date (free-form).",
    )
    preferred_time: Optional[str] = Field(
        default=None,
        description="User's preferred time slot (free-form).",
    )
    location: Optional[str] = Field(
        default=None,
        description="Location preference (city, temple name, or 'home').",
    )
    user_details: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional user-provided details (name, phone, address).",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional free-form context forwarded to the executor.",
    )


# ---------------------------------------------------------------------------
# Booking result model
# ---------------------------------------------------------------------------


class BookingResult(SchemaModel):
    """Immutable result produced by the Booking Service for one user turn.

    The service always returns one of these — it never returns ``None``.
    When booking is not required, ``required`` is ``False`` and
    ``booking_request`` is ``None``.

    Attributes:
        required:         ``True`` when a booking workflow must be triggered.
        status:           Current lifecycle status of this booking.
        booking_request:  Populated ``BookingRequest`` when ``required=True``,
                          otherwise ``None``.
        confirmation_id:  Booking confirmation identifier assigned after
                          successful submission. ``None`` in the placeholder.
        message:          Human-readable status or outcome message.
        confidence:       Planning confidence in [0.0, 1.0].
        metadata:         Optional free-form context forwarded to callers.
    """

    required: bool = Field(
        ...,
        description="True when a booking workflow must be triggered.",
    )
    status: BookingStatus = Field(
        default=BookingStatus.NOT_REQUIRED,
        description="Lifecycle status of this booking.",
    )
    booking_request: Optional[BookingRequest] = Field(
        default=None,
        description="Booking details when required=True, otherwise None.",
    )
    confirmation_id: Optional[str] = Field(
        default=None,
        description="Booking confirmation identifier after successful submission.",
    )
    message: str = Field(
        default="",
        description="Human-readable status or outcome message.",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Planning confidence in [0.0, 1.0].",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional free-form context forwarded to callers.",
    )
