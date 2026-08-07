import os
import shutil
import uuid
from typing import List, Optional

from fastapi import HTTPException, UploadFile

from app.schemas.pandit_schema import PanditApplicationResponse
from app.database.pandit_db import find_pandit_by_email, create_pandit_application
from app.database.user_db import find_user_by_email
from app.services.security import hash_password


UPLOAD_DIR = "uploads"
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}


def save_uploaded_file(file: UploadFile, subfolder: str) -> str:
    ext = os.path.splitext(file.filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}"
        )

    folder = os.path.join(UPLOAD_DIR, subfolder)
    os.makedirs(folder, exist_ok=True)

    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(folder, filename)

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return filepath.replace("\\", "/")


async def execute_pandit_application(
    name: str,
    email: str,
    phone: str,
    password: str,
    confirm_password: str,
    city: str,
    state: str,
    languages: List[str],
    experience: str,
    specialization: str,
    aadhaar_file: Optional[UploadFile],
    certificate_file: Optional[UploadFile],
) -> PanditApplicationResponse:

    if password != confirm_password:
        raise HTTPException(
            status_code=400,
            detail="Password and confirm password do not match."
        )

    existing_application = await find_pandit_by_email(email)
    if existing_application:
        raise HTTPException(
            status_code=409,
            detail="An application with this email already exists."
        )

    existing_user = await find_user_by_email(email)
    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="This email is already registered as a devotee account."
        )

    aadhaar_path = (
        save_uploaded_file(aadhaar_file, "aadhaar")
        if aadhaar_file else None
    )

    certificate_path = (
        save_uploaded_file(certificate_file, "certificates")
        if certificate_file else None
    )

    hashed = hash_password(password)

    application_id = await create_pandit_application(
        name=name,
        email=email,
        phone=phone,
        hashed_password=hashed,
        city=city,
        state=state,
        languages=languages,
        experience=experience,
        specialization=specialization,
        aadhaar_file=aadhaar_path,
        certificate_file=certificate_path,
    )

    return PanditApplicationResponse(
        status="success",
        message="Application received. Our verification team will review it within 24 hours.",
        application_id=application_id,
        application_status="pending",
    )