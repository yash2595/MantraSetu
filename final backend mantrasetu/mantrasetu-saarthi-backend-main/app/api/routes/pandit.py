from typing import List, Optional

from fastapi import APIRouter, Form, File, UploadFile

from app.schemas.pandit_schema import PanditApplicationResponse
from app.controllers.pandit_controller import process_pandit_application

router = APIRouter(
    prefix="/pandit",
    tags=["Pandit"]
)


@router.post("/apply", response_model=PanditApplicationResponse)
async def apply(
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    languages: List[str] = Form(...),
    experience: str = Form(...),
    specialization: str = Form(...),
    gender: Optional[str] = Form(None),
    availability: Optional[str] = Form(None),
    service_areas: Optional[List[str]] = Form(None),
    education: Optional[str] = Form(None),
    gurukul: Optional[str] = Form(None),
    achievements: Optional[List[str]] = Form(None),
    bio: Optional[str] = Form(None),
    aadhaar_file: Optional[UploadFile] = File(None),
    certificate_file: Optional[UploadFile] = File(None),
    gallery_files: Optional[List[UploadFile]] = File(None),
):
    return await process_pandit_application(
        name=name,
        email=email,
        phone=phone,
        password=password,
        confirm_password=confirm_password,
        city=city,
        state=state,
        languages=languages,
        experience=experience,
        specialization=specialization,
        gender=gender,
        availability=availability,
        service_areas=service_areas or [],
        education=education,
        gurukul=gurukul,
        achievements=achievements or [],
        bio=bio,
        aadhaar_file=aadhaar_file,
        certificate_file=certificate_file,
        gallery_files=gallery_files or [],
    )