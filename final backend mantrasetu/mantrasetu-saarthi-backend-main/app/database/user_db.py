from app.database.mongodb import database


user_collection = database["users"]


async def find_user_by_email(email: str):
    return await user_collection.find_one({"email": email})

async def find_user_by_phone(phone: str):
    return await user_collection.find_one({"phone": phone})


async def create_user(name: str, email: str, phone: str | None, hashed_password: str) -> str:
    document = {
        "name": name,
        "email": email,
        "phone": phone,
        "hashed_password": hashed_password,
        "is_verified": False,  # set to True after email verification
    }
    result = await user_collection.insert_one(document)
    return str(result.inserted_id)


async def set_user_verified(email: str) -> None:
    """Mark the user's email as verified."""
    await user_collection.update_one(
        {"email": email},
        {"$set": {"is_verified": True}}
    )