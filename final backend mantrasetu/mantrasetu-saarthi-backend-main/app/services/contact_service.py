from app.database.contact_db import create_contact_message
from app.schemas.contact_schema import (
    ContactRequest,
    ContactResponse,
)


async def execute_contact(
    request: ContactRequest,
) -> ContactResponse:

    contact_id = await create_contact_message(
        name=request.name,
        email=request.email,
        topic=request.topic,
        message=request.message,
    )

    return ContactResponse(
        status="success",
        message="Thank you for reaching out. We will be in touch shortly.",
        contact_id=contact_id,
    )