from app.database.mongodb import database


user_collection = database["users"]


async def find_user_by_email(email: str):
    return await user_collection.find_one({"email": email})


async def create_user(name: str, email: str, phone: str, hashed_password: str) -> str:
    document = {
        "name": name,
        "email": email,
        "phone": phone,
        "hashed_password": hashed_password,
    }
    result = await user_collection.insert_one(document)
    return str(result.inserted_id)