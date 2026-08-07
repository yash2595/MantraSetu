"""Pydantic schemas for Pandit onboarding/verification."""

from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import List, Optional


class PanditApplicationRequest(BaseModel):
    """What the frontend sends us when a Panditji applies to onboard."""

    name: str = Field(..., min_length=1, description="Panditji's full name.")
    email: EmailStr = Field(..., description="Panditji's email address.")
    phone: str = Field(..., min_length=10, max_length=15, description="Panditji's phone number.")
    password: str = Field(..., min_length=6, description="Plain-text password from the form.")
    confirm_password: str = Field(..., description="Must match password.")
    city: str = Field(..., min_length=1)
    state: str = Field(..., min_length=1)
    languages: List[str] = Field(default_factory=list)
    experience: str = Field(..., description="e.g. '5-10 years'")
    specialization: str = Field(..., description="e.g. 'Vedic Pujas & Havan'")
    aadhaar_file: Optional[str] = Field(None, description="Stored file path/reference for Aadhaar.")
    certificate_file: Optional[str] = Field(None, description="Stored file path/reference for certificate.")

    @model_validator(mode="after")
    def passwords_must_match(self):
        if self.password != self.confirm_password:
            raise ValueError("password and confirm_password do not match.")
        return self


class PanditApplicationResponse(BaseModel):
    """What we send back after a successful application submission."""

    status: str
    message: str
    application_id: str
    application_status: str