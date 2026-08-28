from typing import Any
from app.database.mongodb import database


pandit_collection = database["pandit_applications"]
drafts_collection = database["pandit_drafts"]


async def save_pandit_draft(draft_id: str, data: dict):
    # Upsert the draft
    await drafts_collection.update_one(
        {"draft_id": draft_id},
        {"$set": {"draft_id": draft_id, "data": data}},
        upsert=True
    )
    return draft_id

async def get_pandit_draft(draft_id: str):
    return await drafts_collection.find_one({"draft_id": draft_id})


async def find_pandit_by_email(email: str):
    return await pandit_collection.find_one({"email": email})


async def get_all_pandits():
    cursor = pandit_collection.find({})
    pandits = await cursor.to_list(length=1000)
    for p in pandits:
        p["id"] = str(p["_id"])
        del p["_id"]
    return pandits


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