from pydantic import BaseModel, EmailStr, Field


class ContactRequest(BaseModel):
    name: str = Field(..., min_length=2)
    email: EmailStr
    topic: str
    message: str = Field(..., min_length=5)


class ContactResponse(BaseModel):
    status: str
    message: str
    contact_id: str