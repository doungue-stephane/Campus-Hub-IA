from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ── Entrées ───────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    role: str = Field(default="student", pattern="^(student|mentor|club_manager|admin)$")
    promotion: str | None = Field(default=None, max_length=50)
    specialty: str | None = Field(default=None, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Sorties ───────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserPublic(BaseModel):
    id: UUID
    email: EmailStr
    first_name: str | None
    last_name: str | None
    role: str
    promotion: str | None
    specialty: str | None
    bio: str | None
    avatar_url: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
