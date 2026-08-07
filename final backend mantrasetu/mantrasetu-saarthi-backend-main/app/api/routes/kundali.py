from fastapi import APIRouter, Depends

from app.schemas.kundali import (
    GenerateKundaliRequest,
    GenerateKundaliResponse,
    KundaliHistoryItem,
)

from app.controllers.kundali_controller import (
    process_generate_kundali,
    process_get_kundali_history,
)

from app.core.auth_dependency import get_current_user

router = APIRouter(
    prefix="/kundali",
    tags=["Kundali"]
)


@router.post("/generate", response_model=GenerateKundaliResponse)
async def generate_kundali(
    request: GenerateKundaliRequest,
    current_user: dict = Depends(get_current_user),
):
    return await process_generate_kundali(
        request,
        current_user["user_id"],
    )


@router.get("/history", response_model=list[KundaliHistoryItem])
async def get_kundali_history(
    current_user: dict = Depends(get_current_user),
):
    return await process_get_kundali_history(
        current_user["user_id"],
    )