from app.services.navigation_service import NavigationService


class NavigationController:

    def __init__(self):
        self.navigation_service = NavigationService()

    async def navigate(self, ai_response: dict):
        return await self.navigation_service.navigate(ai_response)