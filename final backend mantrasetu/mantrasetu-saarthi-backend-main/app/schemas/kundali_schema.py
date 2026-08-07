from pydantic import BaseModel


class GenerateKundaliRequest(BaseModel):
    name: str
    dob: str
    tob: str
    pob: str
    gender: str


class GenerateKundaliResponse(BaseModel):
    status: str
    message: str
    kundali_id: str


class KundaliHistoryItem(BaseModel):
    kundali_id: str
    name: str
    dob: str
    tob: str
    pob: str
    gender: str