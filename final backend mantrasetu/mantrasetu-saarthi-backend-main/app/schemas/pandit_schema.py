"""Pydantic schemas for Pandit onboarding/verification."""

from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import List, Optional


class PanditApplicationRequest(BaseModel):
    """What the frontend sends us when a Panditji applies to onboard.

    Note: this schema is used for documentation purposes; the actual route
    accepts multipart/form-data (FastAPI Form fields), not JSON.
    """

    # ── Required identity & contact ───────────────────────────────────────────
    name: str = Field(..., min_length=1, description="Panditji's full name.")
    email: EmailStr = Field(..., description="Panditji's email address.")
    phone: str = Field(..., min_length=10, max_length=15, description="Panditji's phone number.")
    password: str = Field(..., min_length=8, description="Plain-text password from the form.")
    confirm_password: str = Field(..., description="Must match password.")
    city: str = Field(..., min_length=1)
    state: str = Field(..., min_length=1)

    # ── Required qualifications ───────────────────────────────────────────────
    languages: List[str] = Field(default_factory=list)
    experience: str = Field(..., description="e.g. '5 years'")
    specializations: List[str] = Field(
        default_factory=list,
        description="Multi-select puja specializations, stored as a list."
    )

    # ── Step 1 extras (optional) ──────────────────────────────────────────────
    gender: str = Field("Male", description="'Male', 'Female', or 'Other'")
    availability_mode: str = Field("Both", description="'Online', 'Offline', or 'Both'")
    service_areas: List[str] = Field(default_factory=list)

    # ── Step 2 extras (optional) ──────────────────────────────────────────────
    education: Optional[str] = Field(None)
    gurukul: Optional[str] = Field(None)
    achievements: List[str] = Field(default_factory=list)
    bio: Optional[str] = Field(None)

    # ── File references (paths set by service layer) ──────────────────────────
    aadhaar_file: Optional[str] = Field(None, description="Stored file path for Aadhaar.")
    certificate_file: Optional[str] = Field(None, description="Stored file path for certificate.")
    gallery_files: List[str] = Field(
        default_factory=list,
        description="Stored file paths for gallery images/videos (max 7)."
    )

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