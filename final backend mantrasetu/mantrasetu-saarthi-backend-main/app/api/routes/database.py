from fastapi import APIRouter
from app.database.conversation_db import save_conversation

router = APIRouter(prefix="/database", tags=["Database"])


@router.post("/test")
async def test_database():
    inserted_id = await save_conversation(
        command="Open Panchang",
        response="Navigated successfully"
    )

    return {
        "message": "Document inserted successfully",
        "id": inserted_id
    }