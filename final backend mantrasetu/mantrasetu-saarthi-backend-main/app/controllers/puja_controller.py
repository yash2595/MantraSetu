from app.services.puja_service import execute_get_puja_list
from app.services.puja_service import execute_get_booking_history


async def process_get_puja_list():
    return await execute_get_puja_list()
from app.schemas.puja_schema import BookPujaRequest
from app.services.puja_service import execute_book_puja


async def process_book_puja(request: BookPujaRequest, user_id: str):
    return await execute_book_puja(request, user_id)
async def process_get_booking_history(user_id: str):
    return await execute_get_booking_history(user_id)