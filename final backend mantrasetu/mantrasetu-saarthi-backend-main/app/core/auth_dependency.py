from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError

from app.services.security import decode_access_token

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """Verify the JWT from the Authorization header and return the user's identity.

    Raises 401 if the token is missing, invalid, or expired.
    """
    token = credentials.credentials

    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    user_id = payload.get("sub")
    email = payload.get("email")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload.")

    return {"user_id": user_id, "email": email}