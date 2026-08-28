from typing import List, Optional

from fastapi import UploadFile

from app.services.pandit_service import execute_pandit_application, execute_get_pandit_list


async def process_get_pandit_list():
    return await execute_get_pandit_list()


async def process_pandit_application(
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
):
    return await execute_pandit_application(
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