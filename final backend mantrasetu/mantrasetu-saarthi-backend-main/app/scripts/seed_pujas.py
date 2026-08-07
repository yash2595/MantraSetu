"""One-time script to seed sample puja data into MongoDB.

Run with: python -m app.scripts.seed_pujas
"""

import asyncio

from app.database.mongodb import database

puja_collection = database["pujas"]

SAMPLE_PUJAS = [
    {
        "id": "griha-pravesh",
        "title": "Griha Pravesh Puja",
        "category": "Home & Family",
        "duration": "3.5 Hours",
        "price": 5100,
        "rating": 4.9,
        "reviewsCount": 142,
        "description": "A traditional housewarming ceremony performed before moving into a new home.",
        "image": "/journey-puja.jpg",
        "popular": True,
    },
    {
        "id": "satyanarayan-puja",
        "title": "Satyanarayan Puja",
        "category": "Home & Family",
        "duration": "2 Hours",
        "price": 3100,
        "rating": 4.8,
        "reviewsCount": 98,
        "description": "A puja performed to seek blessings of Lord Vishnu for prosperity and well-being.",
        "image": "/satyanarayan-puja.jpg",
        "popular": False,
    },
    {
        "id": "vivah-puja",
        "title": "Vivah (Wedding) Puja",
        "category": "Wedding",
        "duration": "4 Hours",
        "price": 15100,
        "rating": 5.0,
        "reviewsCount": 56,
        "description": "Complete wedding ceremony rituals performed by experienced pandits.",
        "image": "/vivah-puja.jpg",
        "popular": True,
    },
]


async def seed():
    await puja_collection.delete_many({})  # clear old data first, avoid duplicates
    result = await puja_collection.insert_many(SAMPLE_PUJAS)
    print(f"Inserted {len(result.inserted_ids)} pujas.")


if __name__ == "__main__":
    asyncio.run(seed())