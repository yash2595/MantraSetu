from pydantic import BaseModel


class NavigationRequest(BaseModel):
    page: str


class NavigationResponse(BaseModel):
    status: str
    message: str