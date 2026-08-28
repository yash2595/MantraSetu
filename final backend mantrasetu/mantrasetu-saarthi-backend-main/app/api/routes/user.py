from fastapi import APIRouter

from app.schemas.user_schema import SignupRequest, SignupResponse
from app.controllers.user_controller import process_signup
from app.schemas.user_schema import LoginRequest, LoginResponse
from app.controllers.user_controller import process_login
from app.services.user_service import execute_google_login, execute_verify_email
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

@router.get("/check-duplicate")
async def check_duplicate(email: str = None, phone: str = None):
    from app.services.user_service import check_duplicate_email_or_phone
    return await check_duplicate_email_or_phone(email, phone)

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    return await process_login(request)

class GoogleLoginRequest(BaseModel):
    credential: str

@router.post("/google", response_model=LoginResponse)
async def google_login(request: GoogleLoginRequest):
    return await execute_google_login(request.credential)


@router.get("/verify-email", summary="Verify email via token link")
async def verify_email(token: str):
    """Called when user clicks the verification link in their email."""
    return await execute_verify_email(token)

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    
    # Check users collection
    from app.database.user_db import find_user_by_email
    devotee = await find_user_by_email(email)
    
    if devotee:
        return {
            "status": "success",
            "user_id": current_user["user_id"],
            "email": email,
            "role": "devotee",
            "name": devotee.get("name", ""),
        }
        
    # Check pandit_applications collection
    from app.database.pandit_db import find_pandit_by_email
    pandit = await find_pandit_by_email(email)
    
    if pandit:
        return {
            "status": "success",
            "user_id": current_user["user_id"],
            "email": email,
            "role": "pandit",
            "name": pandit.get("name", ""),
            "application_status": pandit.get("status", "pending")
        }
        
    # Fallback if not found in DB
    return {
        "status": "success",
        "user_id": current_user["user_id"],
        "email": email,
        "role": "devotee"
    }