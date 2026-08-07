from app.schemas.muhurat_schema import (
    MuhuratRequest,
    MuhuratResponse,
)
from app.services.muhurat_service import execute_find_muhurat


async def process_find_muhurat(
    request: MuhuratRequest,
) -> MuhuratResponse:
    return await execute_find_muhurat(request)