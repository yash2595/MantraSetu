from app.database.kundali_db import (
    create_kundali,
    get_kundali_history_by_user,
)

from app.schemas.kundali_schema import (
    GenerateKundaliRequest,
    GenerateKundaliResponse,
    KundaliHistoryItem,
)


class KundaliService:

    @staticmethod
    async def generate_kundali(
        user_id: str,
        data: GenerateKundaliRequest,
    ) -> GenerateKundaliResponse:

        kundali_id = await create_kundali(
            user_id=user_id,
            name=data.name,
            dob=data.dob,
            tob=data.tob,
            pob=data.pob,
            gender=data.gender,
        )

        return GenerateKundaliResponse(
            status="success",
            message="Kundali generated successfully.",
            kundali_id=kundali_id,
        )

    @staticmethod
    async def get_kundali_history(
        user_id: str,
    ) -> list[KundaliHistoryItem]:

        history = await get_kundali_history_by_user(user_id)

        return [
            KundaliHistoryItem(**item)
            for item in history
        ]