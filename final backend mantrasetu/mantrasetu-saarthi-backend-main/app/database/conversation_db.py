from app.database.mongodb import database


conversation_collection = database["conversations"]


async def save_conversation(command: str, response: str):
    document = {
        "command": command,
        "response": response,
    }

    result = await conversation_collection.insert_one(document)
    return str(result.inserted_id)