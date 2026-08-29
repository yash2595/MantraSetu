"""
MongoDB operations for email verification tokens.
Collection: email_verification_tokens
"""

from datetime import datetime, timedelta, timezone

from app.database.mongodb import database

_collection = database["email_verification_tokens"]


async def create_verification_token(user_id: str, email: str, token: str) -> None:
    """Store a verification token. Expires in 24 h."""
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    await _collection.insert_one(
        {
            "user_id": user_id,
            "email": email,
            "token": token,
            "expires_at": expires_at,
            "used": False,
        }
    )


async def find_verification_token(token: str) -> dict | None:
    """Return the token document if valid, unused, and not expired."""
    now = datetime.now(timezone.utc)
    return await _collection.find_one(
        {"token": token, "used": False, "expires_at": {"$gt": now}}
    )


async def mark_token_used(token: str) -> None:
    """Mark a token as used so it cannot be reused."""
    await _collection.update_one({"token": token}, {"$set": {"used": True}})
