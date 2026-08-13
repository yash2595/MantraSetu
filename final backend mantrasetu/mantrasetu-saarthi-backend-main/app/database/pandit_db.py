from typing import Any
from app.database.mongodb import database


pandit_collection = database["pandit_applications"]


async def find_pandit_by_email(email: str):
    return await pandit_collection.find_one({"email": email})


async def create_pandit_application(
    name: str,
    email: str,
    phone: str,
    hashed_password: str,
    city: str,
    state: str,
    languages: list,
    experience: str,
    specialization: Any,
    gender: str | None = None,
    availability: str | None = None,
    service_areas: list | None = None,
    education: str | None = None,
    gurukul: str | None = None,
    achievements: list | None = None,
    bio: str | None = None,
    aadhaar_file: str | None = None,
    certificate_file: str | None = None,
    gallery_files: list | None = None,
) -> str:
    document = {
        "name": name,
        "email": email,
        "phone": phone,
        "hashed_password": hashed_password,
        "city": city,
        "state": state,
        "languages": languages,
        "experience": experience,
        "specialization": specialization,
        "gender": gender,
        "availability": availability,
        "service_areas": service_areas or [],
        "education": education,
        "gurukul": gurukul,
        "achievements": achievements or [],
        "bio": bio,
        "aadhaar_file": aadhaar_file,
        "certificate_file": certificate_file,
        "gallery_files": gallery_files or [],
        "status": "pending",
        "reviewed_at": None,
        "reviewed_by": None,
        "rejection_reason": None,
    }
    result = await pandit_collection.insert_one(document)
    return str(result.inserted_id)