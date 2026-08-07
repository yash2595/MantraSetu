from pydantic import BaseModel


class MuhuratRequest(BaseModel):
    event_type: str
    city: str
    date: str


class MuhuratTiming(BaseModel):
    label: str
    time: str
    description: str


class MuhuratResponse(BaseModel):
    status: str
    event_type: str
    city: str
    date: str
    timings: list[MuhuratTiming]