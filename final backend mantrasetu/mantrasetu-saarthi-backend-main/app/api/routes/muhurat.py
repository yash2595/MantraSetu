from fastapi import APIRouter, Depends

from app.core.auth_dependency import get_current_user
from app.schemas.muhurat_schema import (
    MuhuratRequest,
    MuhuratResponse,
)
from app.controllers.muhurat_controller import process_find_muhurat


router = APIRouter(
    prefix="/muhurat",
    tags=["Muhurat"],
)


@router.post("/find", response_model=MuhuratResponse)
async def find_muhurat(
    request: MuhuratRequest,
    current_user: dict = Depends(get_current_user),
):
    return await process_find_muhurat(request)