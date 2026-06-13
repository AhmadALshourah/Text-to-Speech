"""Pydantic schemas for users and authentication."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Payload for registering a new account."""

    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    """Payload for logging in (by email)."""

    email: EmailStr
    password: str


class UserOut(BaseModel):
    """Safe, public representation of a user (never includes the password)."""

    id: int
    username: str
    email: EmailStr
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """JWT access token returned after a successful login/registration."""

    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ── Profile management — IDEA-12 ────────────────────────────────────────────

class PasswordChange(BaseModel):
    """Payload for changing the current user's password."""

    current_password: str
    new_password: str = Field(min_length=6, max_length=128)


class ProfileOut(BaseModel):
    """Extended user profile including usage statistics."""

    id: int
    username: str
    email: EmailStr
    created_at: datetime
    total_conversions: int = 0
    monthly_chars_used: int = 0

    model_config = ConfigDict(from_attributes=True)
