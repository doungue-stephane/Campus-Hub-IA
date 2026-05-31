from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


# ── Événement ─────────────────────────────────────────────

class EventCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str | None = None
    location: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    capacity: int | None = Field(default=None, ge=1)
    tags: list[str] = Field(default=[])
    organizer_club_id: UUID | None = None


class EventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = None
    location: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    capacity: int | None = None
    tags: list[str] | None = None
    status: str | None = Field(
        default=None,
        pattern="^(published|cancelled|draft)$"
    )


class EventPublic(BaseModel):
    id: UUID
    title: str
    description: str | None
    organizer_id: UUID | None
    organizer_club_id: UUID | None
    location: str | None
    starts_at: datetime | None
    ends_at: datetime | None
    capacity: int | None
    tags: list | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Inscriptions ──────────────────────────────────────────

class RegistrationPublic(BaseModel):
    id: UUID
    event_id: UUID
    user_id: UUID
    status: str
    registered_at: datetime
    feedback_score: int | None
    feedback_comment: str | None

    model_config = {"from_attributes": True}


class FeedbackCreate(BaseModel):
    score: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


# ── Analytics ─────────────────────────────────────────────

class EventAnalytics(BaseModel):
    event_id: UUID
    title: str
    capacity: int | None
    total_registered: int
    total_cancelled: int
    waitlist_count: int
    fill_rate: float | None        # % de places remplies
    average_feedback: float | None


# ── Recommandation ────────────────────────────────────────

class EventRecommendation(BaseModel):
    event_id: UUID
    title: str
    description: str | None
    starts_at: datetime | None
    location: str | None
    tags: list | None
    relevance_score: float
