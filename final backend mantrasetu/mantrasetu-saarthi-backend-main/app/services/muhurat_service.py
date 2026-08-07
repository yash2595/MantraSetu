from app.schemas.muhurat_schema import (
    MuhuratRequest,
    MuhuratResponse,
    MuhuratTiming,
)


async def execute_find_muhurat(
    request: MuhuratRequest,
) -> MuhuratResponse:
    timings = [
        MuhuratTiming(
            label="Most auspicious",
            time="06:18 AM – 07:54 AM",
            description="Brahma Muhurat · A peaceful window for a sacred start",
        ),
        MuhuratTiming(
            label="Morning window",
            time="09:42 AM – 11:16 AM",
            description="Favourable for preparations and first steps",
        ),
        MuhuratTiming(
            label="Evening window",
            time="04:32 PM – 06:08 PM",
            description="A gentle closing window before sunset",
        ),
    ]

    return MuhuratResponse(
        status="success",
        event_type=request.event_type,
        city=request.city,
        date=request.date,
        timings=timings,
    )