from app.database.mongodb import database


kundali_collection = database["kundali_history"]


async def create_kundali(
    user_id: str,
    name: str,
    dob: str,
    tob: str,
    pob: str,
    gender: str,
) -> str:
    document = {
        "user_id": user_id,
        "name": name,
        "dob": dob,
        "tob": tob,
        "pob": pob,
        "gender": gender,
    }

    result = await kundali_collection.insert_one(document)
    return str(result.inserted_id)


async def get_kundali_history_by_user(user_id: str) -> list[dict]:
    cursor = kundali_collection.find({"user_id": user_id})
    kundalis = await cursor.to_list(length=None)

    for kundali in kundalis:
        kundali["kundali_id"] = str(kundali.pop("_id"))
        kundali.pop("user_id", None)

    return kundalis