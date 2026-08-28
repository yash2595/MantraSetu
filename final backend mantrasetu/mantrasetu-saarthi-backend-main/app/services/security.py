import bcrypt
from fastapi.concurrency import run_in_threadpool


async def hash_password(plain_password: str) -> str:
    """Hash a plain-text password for safe storage."""
    def _hash():
        return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    return await run_in_threadpool(_hash)


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plain-text password against a stored hash."""
    def _verify():
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    return await run_in_threadpool(_verify)

from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError

from app.core.config import settings


def create_access_token(user_id: str, email: str) -> str:
    """Create a signed JWT containing the user's identity."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRY_MINUTES)

    payload = {
        "sub": user_id,      # "sub" = subject, the standard JWT field for "who this token is about"
        "email": email,
        "exp": expire,       # "exp" = expiry, JWT automatically becomes invalid after this time
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Verify a token's signature and expiry, and return its contents.

    Raises JWTError if the token is invalid, tampered with, or expired.
    """
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def create_voice_ticket(user_id: str | None = None, role: str = "guest", client_ip: str = "") -> dict:
    """Create a short-lived (60 seconds) signed ephemeral ticket for WebSocket voice connection."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(seconds=60)
    ticket_type = "authenticated" if user_id else "guest"
    payload = {
        "sub": user_id or "guest",
        "type": ticket_type,
        "role": role,
        "client_ip": client_ip,
        "iat": int(now.timestamp()),
        "exp": expire,
    }
    ticket_secret = getattr(settings, "VOICE_TICKET_SECRET", None) or settings.JWT_SECRET_KEY
    token = jwt.encode(payload, ticket_secret, algorithm=settings.JWT_ALGORITHM)
    return {
        "ticket": token,
        "type": ticket_type,
        "user_id": user_id,
        "expires_in": 60,
    }


def decode_voice_ticket(ticket: str) -> dict:
    """Verify and decode an ephemeral voice ticket."""
    ticket_secret = getattr(settings, "VOICE_TICKET_SECRET", None) or settings.JWT_SECRET_KEY
    return jwt.decode(ticket, ticket_secret, algorithms=[settings.JWT_ALGORITHM])