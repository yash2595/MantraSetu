import os
import secrets

import pymongo.errors
from fastapi import HTTPException

from app.schemas.user_schema import SignupRequest, SignupResponse
from app.schemas.user_schema import LoginRequest, LoginResponse
from app.database.user_db import find_user_by_email, find_user_by_phone, create_user

async def check_duplicate_email_or_phone(email: str | None, phone: str | None) -> dict:
    result = {"is_duplicate": False, "fields": []}
    
    if email:
        try:
            user = await find_user_by_email(email)
            if user:
                result["is_duplicate"] = True
                result["fields"].append("email")
        except pymongo.errors.PyMongoError:
            pass
            
    if phone:
        try:
            user = await find_user_by_phone(phone)
            if user:
                result["is_duplicate"] = True
                result["fields"].append("phone")
        except pymongo.errors.PyMongoError:
            pass
            
    return result
from app.services.security import hash_password, verify_password, create_access_token
from google.oauth2 import id_token
from google.auth.transport import requests


async def execute_signup(request: SignupRequest) -> SignupResponse:
    print(f"[BACKEND-SIGNUP] Endpoint reached for email: {request.email}, name: {request.name}")
    try:
        existing_user = await find_user_by_email(request.email)
    except pymongo.errors.PyMongoError as e:
        print(f"[BACKEND-SIGNUP] Database error: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable. Please try again later.")

    if existing_user:
        print(f"[BACKEND-SIGNUP] 409 Conflict: Email {request.email} already exists")
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists."
        )

    hashed = await hash_password(request.password)

    print(f"[BACKEND-SIGNUP] Writing user document to MongoDB 'users' collection...")
    user_id = await create_user(
        request.name,
        request.email,
        request.phone,
        hashed,
    )
    print(f"[BACKEND-SIGNUP] User document successfully persisted in MongoDB! Inserted ID: {user_id}")

    # ── Send verification email ─────────────────────────────────────────────
    from app.services.email_service import send_verification_email
    from app.database.verification_db import create_verification_token
    from app.core.config import settings

    token = secrets.token_urlsafe(32)
    await create_verification_token(user_id=user_id, email=request.email, token=token)

    # Build the verification URL (BASE_URL configurable via env, defaults to localhost)
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    verify_url = f"{base_url}/auth/verify-email?token={token}"

    print(f"[BACKEND-SIGNUP] Sending verification email to {request.email}...")
    email_sent = await send_verification_email(to_email=request.email, verify_url=verify_url)
    if email_sent:
        print(f"[BACKEND-SIGNUP] Verification email dispatched successfully for {request.email}")
    else:
        print(f"[BACKEND-SIGNUP] WARNING: Verification email dispatch failed for {request.email}")
    # ───────────────────────────────────────────────────────────────────────

    access_token = create_access_token(user_id=user_id, email=request.email)

    return SignupResponse(
        status="success",
        message="Account created successfully. Please check your email to verify your account.",
        user_id=user_id,
        access_token=access_token,
        token_type="bearer",
    )


async def execute_verify_email(token: str) -> dict:
    """Verify the email using a token from the verification link."""
    from app.database.verification_db import find_verification_token, mark_token_used
    from app.database.user_db import set_user_verified

    doc = await find_verification_token(token)
    if not doc:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired verification link. Please request a new one."
        )

    await set_user_verified(doc["email"])
    await mark_token_used(token)

    print(f"[BACKEND-VERIFY] Email verified successfully for {doc['email']}")
    return {"status": "success", "message": "Email verified successfully. You can now log in."}



async def execute_login(request: LoginRequest) -> LoginResponse:
    try:
        user = await find_user_by_email(request.email)
        user_type = "devotee"
        
        if not user:
            from app.database.pandit_db import find_pandit_by_email
            user = await find_pandit_by_email(request.email)
            user_type = "pandit"
            
    except pymongo.errors.PyMongoError as e:
        print(f"[BACKEND-LOGIN] Database error: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable. Please try again later.")

    if not user or not (await verify_password(request.password, user["hashed_password"])):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token(user_id=str(user["_id"]), email=user["email"])

    return LoginResponse(
        status="success",
        message="Login successful.",
        user_id=str(user["_id"]),
        name=user["name"],
        access_token=token,
        token_type="bearer",
        # We could pass user_type in the future if we extend LoginResponse
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

        try:
            user = await find_user_by_email(email)
        except pymongo.errors.PyMongoError as e:
            print(f"[BACKEND-GOOGLE-LOGIN] Database error: {e}")
            raise HTTPException(status_code=503, detail="Service unavailable. Please try again later.")

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