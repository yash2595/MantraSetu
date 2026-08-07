import bcrypt


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password for safe storage."""
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plain-text password against a stored hash."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

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