from app.services.kundali_service import KundaliService


async def process_generate_kundali(request, user_id: str):
    return await KundaliService.generate_kundali(
        user_id=user_id,
        data=request,
    )


async def process_get_kundali_history(user_id: str):
    return await KundaliService.get_kundali_history(
        user_id=user_id,
    )