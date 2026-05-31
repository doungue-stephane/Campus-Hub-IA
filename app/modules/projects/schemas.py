from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


# ── Compétences requises dans un projet ───────────────────

class RequiredSkill(BaseModel):
    skill_id: UUID
    level: str = Field(pattern="^(beginner|intermediate|advanced|expert)$")
    weight: float = Field(default=1.0, ge=0.1, le=1.0)


# ── Projet ────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str | None = None
    required_skills: list[RequiredSkill] = Field(default=[])
    team_size_target: int | None = Field(default=None, ge=1, le=50)
    duration_weeks: int | None = Field(default=None, ge=1)
    type: str | None = Field(
        default=None,
        pattern="^(open_innovation|personal|club)$"
    )


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = None
    required_skills: list[RequiredSkill] | None = None
    team_size_target: int | None = None
    duration_weeks: int | None = None
    status: str | None = Field(
        default=None,
        pattern="^(open|in_progress|closed)$"
    )
    type: str | None = None


class ProjectPublic(BaseModel):
    id: UUID
    title: str
    description: str | None
    required_skills: list | None
    team_size_target: int | None
    duration_weeks: int | None
    supervisor_id: UUID | None
    status: str
    type: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Candidatures ──────────────────────────────────────────

class ApplicationPublic(BaseModel):
    id: UUID
    project_id: UUID
    student_id: UUID
    status: str
    match_score: float | None
    applied_at: datetime

    model_config = {"from_attributes": True}


class ApplicationStatusUpdate(BaseModel):
    status: str = Field(pattern="^(accepted|rejected)$")


# ── Résultats de matching ─────────────────────────────────

class StudentMatchResult(BaseModel):
    user_id: UUID
    score: float
    score_percent: int   # score * 100 arrondi


class ProjectMatchResult(BaseModel):
    project_id: UUID
    title: str
    description: str | None
    score: float
    score_percent: int


# ── Membres ───────────────────────────────────────────────

class ProjectMemberPublic(BaseModel):
    project_id: UUID
    user_id: UUID
    role: str | None
    joined_at: datetime

    model_config = {"from_attributes": True}
