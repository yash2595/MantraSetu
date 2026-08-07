from app.database.conversation_db import conversation_collection
from app.schemas.navigation import NavigationResponse


class NavigationService:

    async def navigate(self, ai_response: dict):

        page = ai_response["page"]

        document = {
            "intent": ai_response["intent"],
            "page": ai_response["page"],
            "confidence": ai_response["confidence"],
            "status": "success"
        }

        await conversation_collection.insert_one(document)

        return NavigationResponse(
            status="success",
            message=f"Navigation request received for '{page}'"
        )