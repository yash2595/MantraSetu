from fastapi import APIRouter
from app.schemas.navigation import NavigationRequest, NavigationResponse
from app.controllers.navigation_controller import NavigationController

router = APIRouter(
    prefix="/navigation",
    tags=["Navigation"]
)

navigation_controller = NavigationController()


@router.post("", response_model=NavigationResponse)
async def navigate(request: NavigationRequest):

    ai_response = {
        "intent": "navigation",
        "page": request.page,
        "confidence": 1.0
    }

    return await navigation_controller.navigate(ai_response)