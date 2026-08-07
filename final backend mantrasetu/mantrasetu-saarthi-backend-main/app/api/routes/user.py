from fastapi import APIRouter

from app.schemas.user_schema import SignupRequest, SignupResponse
from app.controllers.user_controller import process_signup
from app.schemas.user_schema import LoginRequest, LoginResponse
from app.controllers.user_controller import process_login
from app.services.user_service import execute_google_login
from pydantic import BaseModel
from fastapi import Depends
from app.core.auth_dependency import get_current_user

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)


@router.post("/signup", response_model=SignupResponse)
async def signup(request: SignupRequest):
    return await process_signup(request)

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    return await process_login(request)

class GoogleLoginRequest(BaseModel):
    credential: str

@router.post("/google", response_model=LoginResponse)
async def google_login(request: GoogleLoginRequest):
    return await execute_google_login(request.credential)

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "status": "success",
        "user_id": current_user["user_id"],
        "email": current_user["email"],
    }