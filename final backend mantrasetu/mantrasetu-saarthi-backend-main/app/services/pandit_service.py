import os
import uuid
from typing import List, Optional

import pymongo
from fastapi import HTTPException, UploadFile

from app.schemas.pandit_schema import PanditApplicationResponse
from app.database.pandit_db import find_pandit_by_email, create_pandit_application
from app.database.user_db import find_user_by_email
from app.services.security import hash_password
from app.utils.file_handler import save_uploaded_file
from app.database.pandit_db import get_all_pandits


async def execute_get_pandit_list() -> List[dict]:
    pandits = await get_all_pandits()
    return pandits



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
    gender: Optional[str] = None,
    availability: Optional[str] = None,
    service_areas: Optional[List[str]] = None,
    education: Optional[str] = None,
    gurukul: Optional[str] = None,
    achievements: Optional[List[str]] = None,
    bio: Optional[str] = None,
    aadhaar_file: Optional[UploadFile] = None,
    certificate_file: Optional[UploadFile] = None,
    gallery_files: Optional[List[UploadFile]] = None,
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
            detail="Is email address se pehle se ek application maujood hai."
        )

    existing_user = await find_user_by_email(email)
    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Yeh email pehle se hi ek devotee account ke saath registered hai."
        )

    aadhaar_path = (
        await save_uploaded_file(aadhaar_file, "aadhaar")
        if aadhaar_file else None
    )

    certificate_path = (
        await save_uploaded_file(certificate_file, "certificates")
        if certificate_file else None
    )

    saved_gallery_paths: List[str] = []
    if gallery_files:
        for gfile in gallery_files:
            if gfile and gfile.filename:
                gpath = await save_uploaded_file(gfile, "gallery")
                saved_gallery_paths.append(gpath)

    # Specialization parsing: accept list or comma-separated string
    spec_list: List[str] = []
    if isinstance(specialization, str):
        spec_list = [s.strip() for s in specialization.split(",") if s.strip()]
    elif isinstance(specialization, list):
        spec_list = specialization
    else:
        spec_list = [str(specialization)]

    hashed = await hash_password(password)

    try:
        print(f"[BACKEND-PANDIT-APPLY] Writing Pandit application document to MongoDB 'pandit_applications' collection...")
        application_id = await create_pandit_application(
            name=name,
            email=email,
            phone=phone,
            hashed_password=hashed,
            city=city,
            state=state,
            languages=languages,
            experience=experience,
            specialization=spec_list if len(spec_list) > 1 else specialization,
            gender=gender,
            availability=availability,
            service_areas=service_areas or [],
            education=education,
            gurukul=gurukul,
            achievements=achievements or [],
            bio=bio,
            aadhaar_file=aadhaar_path,
            certificate_file=certificate_path,
            gallery_files=saved_gallery_paths,
        )
        print(f"[BACKEND-PANDIT-APPLY] Pandit application persisted in MongoDB! Inserted ID: {application_id}")
    except pymongo.errors.DuplicateKeyError:
        print(f"[BACKEND-PANDIT-APPLY] Duplicate Key Error")
        raise HTTPException(
            status_code=409,
            detail="Is email ya mobile number se pehle se ek application maujood hai."
        )
    except Exception as e:
        print(f"[BACKEND-PANDIT-APPLY] DB insert error: {e}")
        raise e

    return PanditApplicationResponse(
        status="success",
        message="Application received. Our verification team will review it within 24 hours.",
        application_id=application_id,
        application_status="pending",
    )