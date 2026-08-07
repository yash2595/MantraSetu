from app.database.puja_db import get_all_pujas, create_booking, get_bookings_by_user
from app.schemas.puja_schema import (
    PujaResponse,
    BookPujaRequest,
    BookPujaResponse,
    BookingHistoryItem,
)


async def execute_get_puja_list() -> list[PujaResponse]:
    pujas = await get_all_pujas()
    return [PujaResponse(**puja) for puja in pujas]


async def execute_book_puja(request: BookPujaRequest, user_id: str) -> BookPujaResponse:
    booking_id = await create_booking(
        user_id=user_id,
        puja_id=request.puja_id,
        city=request.city,
        date=request.date,
        time=request.time,
        devotee_name=request.devotee_name,
        phone=request.phone,
    )

    return BookPujaResponse(
        status="success",
        booking_id=booking_id,
    )


async def execute_get_booking_history(user_id: str) -> list[BookingHistoryItem]:
    bookings = await get_bookings_by_user(user_id)
    return [BookingHistoryItem(**booking) for booking in bookings]