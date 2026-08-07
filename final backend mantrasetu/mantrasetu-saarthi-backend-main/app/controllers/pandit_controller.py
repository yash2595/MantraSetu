from typing import List, Optional

from fastapi import UploadFile

from app.services.pandit_service import execute_pandit_application


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
    aadhaar_file: Optional[UploadFile],
    certificate_file: Optional[UploadFile],
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
        aadhaar_file=aadhaar_file,
        certificate_file=certificate_file,
    )