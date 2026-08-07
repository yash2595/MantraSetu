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
    specialization: str,
    aadhaar_file: str | None,
    certificate_file: str | None,
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
        "aadhaar_file": aadhaar_file,
        "certificate_file": certificate_file,
        "status": "pending",
        "reviewed_at": None,
        "reviewed_by": None,
        "rejection_reason": None,
    }
    result = await pandit_collection.insert_one(document)
    return str(result.inserted_id)