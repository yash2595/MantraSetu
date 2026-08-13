from fastapi import HTTPException

from app.schemas.user_schema import SignupRequest, SignupResponse
from app.schemas.user_schema import LoginRequest, LoginResponse
from app.database.user_db import find_user_by_email, create_user
from app.services.security import hash_password, verify_password, create_access_token
from google.oauth2 import id_token
from google.auth.transport import requests
import os


async def execute_signup(request: SignupRequest) -> SignupResponse:
    print(f"[BACKEND-SIGNUP] Endpoint reached for email: {request.email}, name: {request.name}")
    existing_user = await find_user_by_email(request.email)

    if existing_user:
        print(f"[BACKEND-SIGNUP] 409 Conflict: Email {request.email} already exists")
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists."
        )

    hashed = hash_password(request.password)

    print(f"[BACKEND-SIGNUP] Writing user document to MongoDB 'users' collection...")
    user_id = await create_user(
        request.name,
        request.email,
        request.phone,
        hashed,
    )
    print(f"[BACKEND-SIGNUP] User document successfully persisted in MongoDB! Inserted ID: {user_id}")

    token = create_access_token(user_id=user_id, email=request.email)

    return SignupResponse(
        status="success",
        message="Account created successfully.",
        user_id=user_id,
        access_token=token,
        token_type="bearer",
    )


async def execute_login(request: LoginRequest) -> LoginResponse:
    user = await find_user_by_email(request.email)

    if not user or not verify_password(request.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token(user_id=str(user["_id"]), email=user["email"])

    return LoginResponse(
        status="success",
        message="Login successful.",
        user_id=str(user["_id"]),
        name=user["name"],
        access_token=token,
        token_type="bearer",
    )

async def execute_google_login(credential: str) -> LoginResponse:
    try:
        from app.core.config import settings
        # Validate Google credential
        client_id = settings.GOOGLE_CLIENT_ID
        idinfo = id_token.verify_oauth2_token(credential, requests.Request(), client_id)
            
        email = idinfo.get("email")
        name = idinfo.get("name", "Google User")
        
        if not email:
            raise HTTPException(status_code=400, detail="Google token missing email")

        user = await find_user_by_email(email)

        if not user:
            # Create a shadow user (without password)
            user_id = await create_user(
                name=name,
                email=email,
                phone=None,
                hashed_password="oauth2_google" # Placeholder
            )
            user = {"_id": user_id, "email": email, "name": name}

        # Issue MantraSetu JWT
        token = create_access_token(user_id=str(user["_id"]), email=user["email"])

        return LoginResponse(
            status="success",
            message="Google login successful.",
            user_id=str(user["_id"]),
            name=user.get("name", name),
            access_token=token,
            token_type="bearer",
        )

    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {str(e)}")