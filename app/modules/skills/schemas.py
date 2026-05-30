from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


VALID_CATEGORIES = {"technical", "soft", "language", "certification"}
VALID_LEVELS = {"beginner", "intermediate", "advanced", "expert"}


# ── Skill (référentiel) ───────────────────────────────────

class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    category: str = Field(pattern="^(technical|soft|language|certification)$")
    taxonomy_ref: str | None = Field(default=None, max_length=50)


class SkillPublic(BaseModel):
    id: UUID
    name: str
    category: str
    taxonomy_ref: str | None

    model_config = {"from_attributes": True}


# ── UserSkill (compétences du profil) ─────────────────────

class UserSkillAdd(BaseModel):
    skill_id: UUID
    level: str = Field(pattern="^(beginner|intermediate|advanced|expert)$")


class UserSkillUpdate(BaseModel):
    level: str = Field(pattern="^(beginner|intermediate|advanced|expert)$")


class UserSkillPublic(BaseModel):
    id: UUID
    skill_id: UUID
    skill_name: str
    skill_category: str
    level: str
    validated_by: UUID | None
    validated_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Export portfolio ──────────────────────────────────────

class SkillExportRow(BaseModel):
    skill_name: str
    category: str
    level: str
    validated: bool
