from fastapi import APIRouter
from fastapi import Depends


from app.schemas.puja_schema import PujaResponse
from app.controllers.puja_controller import process_get_puja_list
from app.schemas.puja_schema import BookPujaRequest, BookPujaResponse
from app.controllers.puja_controller import process_book_puja
from app.core.auth_dependency import get_current_user
from app.schemas.puja_schema import BookingHistoryItem
from app.controllers.puja_controller import process_get_booking_history


router = APIRouter(
    prefix="/puja",
    tags=["Puja"]
)


@router.get("/list", response_model=list[PujaResponse])
async def get_puja_list():
    return await process_get_puja_list()

@router.post("/book", response_model=BookPujaResponse)
async def book_puja(
    request: BookPujaRequest,
    current_user: dict = Depends(get_current_user),
):
    return await process_book_puja(request, current_user["user_id"])

@router.get("/history", response_model=list[BookingHistoryItem])
async def get_booking_history(current_user: dict = Depends(get_current_user)):
    return await process_get_booking_history(current_user["user_id"])