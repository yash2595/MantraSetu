from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

from app.core.config import settings

MONGODB_URI = settings.MONGODB_URI
DATABASE_NAME = settings.DATABASE_NAME

client = AsyncIOMotorClient(MONGODB_URI)

database = client[DATABASE_NAME]


async def check_database_connection():
    try:
        print("[INFO] Creating MongoDB indexes...")
        await database["users"].create_index("email", unique=True)
        await database["pandit_applications"].create_index("email", unique=True)
        print("[INFO] MongoDB indexes created successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to create MongoDB indexes: {e}")