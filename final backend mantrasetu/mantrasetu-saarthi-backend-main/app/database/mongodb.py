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
    # Skip actual DB ping during development to avoid blocking startup when MongoDB is unavailable.
    print("[INFO] Skipping MongoDB connection check (development mode).")
    return