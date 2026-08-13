"""Pydantic schemas for user signup and login."""

from pydantic import BaseModel, EmailStr, Field, model_validator


class SignupRequest(BaseModel):
    """What the frontend sends us when someone signs up."""

    name: str = Field(..., min_length=1, description="User's full name.")
    email: EmailStr = Field(..., description="User's email address.")
    phone: str = Field(..., min_length=10, max_length=15, description="User's phone number.")
    password: str = Field(..., min_length=6, description="Plain-text password from the form.")
    confirm_password: str = Field(..., description="Must match password.")

    @model_validator(mode="after")
    def passwords_must_match(self):
        if self.password != self.confirm_password:
            raise ValueError("password and confirm_password do not match.")
        return self


class SignupResponse(BaseModel):
    """What we send back after a successful signup."""

    status: str
    message: str
    user_id: str
    access_token: str | None = None
    token_type: str = "bearer"
    
class LoginRequest(BaseModel):
    """What the frontend sends us when someone logs in."""

    email: EmailStr = Field(..., description="User's email address.")
    password: str = Field(..., description="Plain-text password from the form.")


class LoginResponse(BaseModel):
    """What we send back after a login attempt."""

    status: str
    message: str
    user_id: str
    name: str
    
class LoginResponse(BaseModel):
    """What we send back after a login attempt."""

    status: str
    message: str
    user_id: str
    name: str
    access_token: str
    token_type: str = "bearer"    
    