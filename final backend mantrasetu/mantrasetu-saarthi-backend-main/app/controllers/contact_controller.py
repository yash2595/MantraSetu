from app.schemas.contact_schema import ContactRequest
from app.services.contact_service import execute_contact


async def process_contact(request: ContactRequest):
    return await execute_contact(request)