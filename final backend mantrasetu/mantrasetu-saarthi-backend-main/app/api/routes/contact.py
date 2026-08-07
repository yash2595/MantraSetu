from fastapi import APIRouter

from app.controllers.contact_controller import process_contact
from app.schemas.contact_schema import (
    ContactRequest,
    ContactResponse,
)

router = APIRouter(
    prefix="/contact",
    tags=["Contact"],
)


@router.post(
    "",
    response_model=ContactResponse,
)
async def submit_contact(request: ContactRequest):
    return await process_contact(request)