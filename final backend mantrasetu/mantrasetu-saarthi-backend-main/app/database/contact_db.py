from datetime import datetime

from app.database.mongodb import database

contact_collection = database["contact_messages"]


async def create_contact_message(
    name: str,
    email: str,
    topic: str,
    message: str,
) -> str:

    document = {
        "name": name,
        "email": email,
        "topic": topic,
        "message": message,
        "created_at": datetime.utcnow(),
    }

    result = await contact_collection.insert_one(document)

    return str(result.inserted_id)