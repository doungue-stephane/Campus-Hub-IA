from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


# ── Paires de mentorat ────────────────────────────────────

class PairCreate(BaseModel):
    mentor_id: UUID
    mentee_id: UUID


class PairStatusUpdate(BaseModel):
    status: str = Field(pattern="^(active|paused|completed)$")


class PairPublic(BaseModel):
    id: UUID
    mentor_id: UUID
    mentee_id: UUID
    match_score: float | None
    status: str
    started_at: datetime

    model_config = {"from_attributes": True}


# ── Sessions ──────────────────────────────────────────────

class SessionCreate(BaseModel):
    pair_id: UUID
    scheduled_at: datetime
    duration_minutes: int | None = Field(default=None, ge=15, le=180)
    notes: str | None = None


class SessionUpdate(BaseModel):
    status: str | None = Field(
        default=None,
        pattern="^(scheduled|done|cancelled)$"
    )
    notes: str | None = None
    duration_minutes: int | None = None
    mentor_rating: int | None = Field(default=None, ge=1, le=5)
    mentee_rating: int | None = Field(default=None, ge=1, le=5)
    feedback_mentor: str | None = None
    feedback_mentee: str | None = None


class SessionPublic(BaseModel):
    id: UUID
    pair_id: UUID
    scheduled_at: datetime | None
    duration_minutes: int | None
    notes: str | None
    status: str
    mentor_rating: int | None
    mentee_rating: int | None
    feedback_mentor: str | None
    feedback_mentee: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Messages ──────────────────────────────────────────────

class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class MessagePublic(BaseModel):
    id: UUID
    pair_id: UUID
    sender_id: UUID
    content: str
    read_at: datetime | None
    sent_at: datetime

    model_config = {"from_attributes": True}


# ── Dashboard mentor ──────────────────────────────────────

class MentorDashboard(BaseModel):
    total_mentees: int
    active_pairs: int
    total_sessions: int
    sessions_done: int
    average_rating: float | None
