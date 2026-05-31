from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


# ── Club ──────────────────────────────────────────────────

class ClubCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = None
    logo_url: str | None = None
    manager_id: UUID | None = None


class ClubUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = None
    logo_url: str | None = None
    manager_id: UUID | None = None


class ClubPublic(BaseModel):
    id: UUID
    name: str
    description: str | None
    logo_url: str | None
    manager_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Membres ───────────────────────────────────────────────

class ClubMemberPublic(BaseModel):
    id: UUID
    club_id: UUID
    user_id: UUID
    role: str
    joined_at: datetime
    left_at: datetime | None

    model_config = {"from_attributes": True}


# ── Offres de bénévolat ───────────────────────────────────

class ClubOfferCreate(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    description: str | None = None
    required_skills: list[dict] = Field(default=[])


class ClubOfferUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    required_skills: list[dict] | None = None
    status: str | None = Field(default=None, pattern="^(open|closed)$")


class ClubOfferPublic(BaseModel):
    id: UUID
    club_id: UUID
    title: str
    description: str | None
    required_skills: list | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── KPIs ──────────────────────────────────────────────────

class ClubKPIs(BaseModel):
    club_id: UUID
    club_name: str
    total_members: int
    active_members: int
    retention_rate: float          # % membres encore actifs
    total_offers: int
    open_offers: int


class ClubBenchmark(BaseModel):
    rank: int
    club_id: UUID
    club_name: str
    total_members: int
    active_members: int
    open_offers: int
