"""
conftest.py for the backend test suite.

Motor (motor.motor_asyncio.AsyncIOMotorClient) binds to the asyncio event
loop that is active when it is first used. pytest-anyio creates a new event
loop for each async test, resulting in a RuntimeError if the client is imported
globally at load-time (since it remains bound to a different or closed event loop).

Fix: Re-initialize and rebind the database client and all collection variables
to a fresh client created inside the current test's event loop.
"""
import pytest
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

import app.database.mongodb
import app.database.pandit_db
import app.database.user_db
import app.database.puja_db
import app.database.kundali_db
import app.database.conversation_db
import app.database.contact_db


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
async def patch_mongodb_client():
    # Instantiate client and database under the currently running test loop
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    database = client[settings.DATABASE_NAME]

    # Rebind the database module variables
    app.database.mongodb.client = client
    app.database.mongodb.database = database

    # Rebind collection properties inside load-time imported DB modules
    app.database.pandit_db.database = database
    app.database.pandit_db.pandit_collection = database["pandit_applications"]

    app.database.user_db.database = database
    app.database.user_db.user_collection = database["users"]

    app.database.puja_db.database = database
    app.database.puja_db.puja_collection = database["pujas"]

    app.database.kundali_db.database = database
    app.database.kundali_db.kundali_collection = database["kundali_profiles"]

    app.database.conversation_db.database = database
    app.database.conversation_db.conversation_collection = database["conversations"]

    app.database.contact_db.database = database
    app.database.contact_db.contact_collection = database["contacts"]

    yield

    # Cleanup the test client connection pool
    client.close()
