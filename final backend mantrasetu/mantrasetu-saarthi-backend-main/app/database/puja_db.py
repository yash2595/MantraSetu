from app.database.mongodb import database


puja_collection = database["pujas"]


async def get_all_pujas() -> list[dict]:
    cursor = puja_collection.find({}, {"_id": 0})
    return await cursor.to_list(length=None)
booking_collection = database["puja_bookings"]


async def create_booking(
    user_id: str,
    puja_id: str,
    city: str,
    date: str,
    time: str,
    devotee_name: str,
    phone: str,
) -> str:
    document = {
        "user_id": user_id,
        "puja_id": puja_id,
        "city": city,
        "date": date,
        "time": time,
        "devotee_name": devotee_name,
        "phone": phone,
        "status": "confirmed",
    }
    result = await booking_collection.insert_one(document)
    return str(result.inserted_id)
async def get_bookings_by_user(user_id: str) -> list[dict]:
    cursor = booking_collection.find({"user_id": user_id})
    bookings = await cursor.to_list(length=None)

    for booking in bookings:
        booking["booking_id"] = str(booking.pop("_id"))
        booking.pop("user_id", None)

    return bookings