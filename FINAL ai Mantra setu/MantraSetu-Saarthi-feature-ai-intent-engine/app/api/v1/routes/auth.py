from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
import uuid

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginPayload(BaseModel):
    email: str
    password: str
    remember: Optional[bool] = False

class GooglePayload(BaseModel):
    credential: str

class SignupPayload(BaseModel):
    name: str
    email: str
    password: Optional[str] = None
    user_type: Optional[str] = "devotee"

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginPayload):
    # Stub implementation
    if not payload.email or not payload.password:
        raise HTTPException(status_code=400, detail="Email and password required")
    
    return AuthResponse(
        access_token=f"mock_token_{uuid.uuid4().hex}",
        user={"id": "u123", "name": "Test User", "email": payload.email, "user_type": "devotee"}
    )

@router.post("/google", response_model=AuthResponse)
async def google_login(payload: GooglePayload):
    return AuthResponse(
        access_token=f"mock_token_{uuid.uuid4().hex}",
        user={"id": "u123", "name": "Google User", "email": "google@example.com", "user_type": "devotee"}
    )

@router.post("/signup", response_model=AuthResponse)
async def signup(payload: SignupPayload):
    return AuthResponse(
        access_token=f"mock_token_{uuid.uuid4().hex}",
        user={"id": "u123", "name": payload.name, "email": payload.email, "user_type": payload.user_type}
    )

@router.get("/me")
async def get_me(request: Request):
    # Stub implementation - return mock user if Authorization header exists
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return {"id": "u123", "name": "Test User", "email": "test@example.com", "user_type": "devotee"}
