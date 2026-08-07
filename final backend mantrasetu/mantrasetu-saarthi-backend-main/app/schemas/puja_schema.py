"""Pydantic schemas for the Puja module."""

from pydantic import BaseModel


class PujaResponse(BaseModel):
    """A single puja, as returned to the frontend."""

    id: str
    title: str
    category: str
    duration: str
    price: int
    rating: float
    reviewsCount: int
    description: str
    image: str
    popular: bool = False


class BookPujaRequest(BaseModel):
    """What the frontend sends when confirming a booking."""

    puja_id: str
    city: str
    date: str
    time: str
    devotee_name: str
    phone: str


class BookPujaResponse(BaseModel):
    """What we send back after a successful booking."""

    status: str
    booking_id: str
    
class BookingHistoryItem(BaseModel):
    """A single past booking, as returned to the frontend."""

    booking_id: str
    puja_id: str
    city: str
    date: str
    time: str
    devotee_name: str
    phone: str
    status: str