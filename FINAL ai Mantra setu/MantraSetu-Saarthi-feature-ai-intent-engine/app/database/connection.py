"""Database connection manager with PyMongo singleton connection pooling."""

from __future__ import annotations

import logging
import os
from typing import Any

import pymongo

logger = logging.getLogger(__name__)

_mongo_client: pymongo.MongoClient[dict[str, Any]] | None = None


def init_db_client() -> None:
    """Initialize persistent MongoDB connection pool at application startup."""
    global _mongo_client
    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri or "<username>" in mongo_uri:
        mongo_uri = "mongodb://127.0.0.1:27017/mantrasetu"
        logger.info("[DATABASE] Using local MongoDB fallback URI: %s", mongo_uri)

    if _mongo_client is None:
        try:
            _mongo_client = pymongo.MongoClient(
                mongo_uri,
                maxPoolSize=50,
                minPoolSize=5,
                serverSelectionTimeoutMS=3000,
            )
            # Ping database to verify connection pool health
            _mongo_client.admin.command("ping")
            logger.info("[DATABASE] Persistent MongoDB connection pool initialized (maxPoolSize=50).")
        except Exception as e:
            logger.error("[DATABASE] Persistent MongoDB connection pool initialization failed: %s", e)
            _mongo_client = None


def close_db_client() -> None:
    """Close persistent MongoDB connection pool at application shutdown."""
    global _mongo_client
    if _mongo_client is not None:
        try:
            _mongo_client.close()
            logger.info("[DATABASE] Persistent MongoDB connection pool closed.")
        except Exception as e:
            logger.error("[DATABASE] Error closing MongoDB connection pool: %s", e)
        finally:
            _mongo_client = None


def get_mongo_client() -> pymongo.MongoClient[dict[str, Any]] | None:
    """Get active singleton MongoDB client instance."""
    global _mongo_client
    if _mongo_client is None:
        init_db_client()
    return _mongo_client


def get_db(db_name: str | None = None) -> Any | None:
    """Get MongoDB database handle from shared connection pool."""
    client = get_mongo_client()
    if client is None:
        return None
    mongo_uri = os.getenv("MONGODB_URI", "")
    target_db_name = (
        db_name
        or os.getenv("DATABASE_NAME")
        or (mongo_uri.split("?")[0].rstrip("/").split("/")[-1] if mongo_uri else "mantrasetu")
        or "mantrasetu"
    )
    return client[target_db_name]
