from app.schemas.user_schema import SignupRequest
from app.services.user_service import execute_signup
from app.schemas.user_schema import LoginRequest
from app.services.user_service import execute_login


async def process_signup(request: SignupRequest):
    return await execute_signup(request)

async def process_login(request: LoginRequest):
    return await execute_login(request)