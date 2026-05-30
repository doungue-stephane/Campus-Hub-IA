from uuid import UUID
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.skills.models import Skill, UserSkill
from app.modules.skills.schemas import (
    SkillCreate,
    SkillPublic,
    UserSkillAdd,
    UserSkillPublic,
    UserSkillUpdate,
)


# ── Référentiel de compétences ────────────────────────────

async def list_skills(
    db: AsyncSession,
    category: str | None = None,
    search: str | None = None,
) -> list[Skill]:
    query = select(Skill).order_by(Skill.category, Skill.name)
    if category:
        query = query.where(Skill.category == category)
    if search:
        query = query.where(Skill.name.ilike(f"%{search}%"))
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_skill(data: SkillCreate, db: AsyncSession) -> Skill:
    # Vérifie l'unicité
    result = await db.execute(select(Skill).where(Skill.name == data.name))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La compétence '{data.name}' existe déjà dans le référentiel",
        )
    skill = Skill(**data.model_dump())
    db.add(skill)
    await db.flush()
    return skill


# ── Compétences utilisateur ───────────────────────────────

async def get_user_skills(user_id: UUID, db: AsyncSession) -> list[UserSkillPublic]:
    result = await db.execute(
        select(UserSkill)
        .where(UserSkill.user_id == user_id)
        .options(selectinload(UserSkill.skill))
        .order_by(UserSkill.created_at.desc())
    )
    rows = result.scalars().all()

    return [
        UserSkillPublic(
            id=r.id,
            skill_id=r.skill_id,
            skill_name=r.skill.name,
            skill_category=r.skill.category,
            level=r.level,
            validated_by=r.validated_by,
            validated_at=r.validated_at,
            created_at=r.created_at,
        )
        for r in rows
    ]


async def add_user_skill(
    user_id: UUID, data: UserSkillAdd, db: AsyncSession
) -> UserSkill:
    # Vérifier que la compétence existe dans le référentiel
    skill_result = await db.execute(select(Skill).where(Skill.id == data.skill_id))
    if not skill_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compétence introuvable dans le référentiel",
        )

    # Vérifier que l'utilisateur ne l'a pas déjà
    existing = await db.execute(
        select(UserSkill).where(
            UserSkill.user_id == user_id,
            UserSkill.skill_id == data.skill_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tu possèdes déjà cette compétence dans ton profil",
        )

    user_skill = UserSkill(user_id=user_id, skill_id=data.skill_id, level=data.level)
    db.add(user_skill)
    await db.flush()
    return user_skill


async def update_user_skill(
    user_id: UUID, skill_id: UUID, data: UserSkillUpdate, db: AsyncSession
) -> UserSkill:
    result = await db.execute(
        select(UserSkill).where(
            UserSkill.user_id == user_id,
            UserSkill.skill_id == skill_id,
        )
    )
    user_skill = result.scalar_one_or_none()
    if not user_skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compétence non trouvée dans ton profil",
        )
    user_skill.level = data.level
    return user_skill


async def remove_user_skill(user_id: UUID, skill_id: UUID, db: AsyncSession) -> None:
    result = await db.execute(
        select(UserSkill).where(
            UserSkill.user_id == user_id,
            UserSkill.skill_id == skill_id,
        )
    )
    user_skill = result.scalar_one_or_none()
    if not user_skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compétence non trouvée dans ton profil",
        )
    await db.delete(user_skill)


async def validate_skill(
    target_user_id: UUID,
    skill_id: UUID,
    validator_id: UUID,
    db: AsyncSession,
) -> UserSkill:
    # On ne peut pas valider ses propres compétences
    if target_user_id == validator_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tu ne peux pas valider tes propres compétences",
        )

    result = await db.execute(
        select(UserSkill).where(
            UserSkill.user_id == target_user_id,
            UserSkill.skill_id == skill_id,
        )
    )
    user_skill = result.scalar_one_or_none()
    if not user_skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compétence introuvable pour cet utilisateur",
        )
    if user_skill.validated_by:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette compétence est déjà validée",
        )

    user_skill.validated_by = validator_id
    user_skill.validated_at = datetime.now(timezone.utc)
    return user_skill
