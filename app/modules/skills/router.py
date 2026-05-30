from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.modules.skills import service
from app.modules.skills.schemas import (
    SkillCreate,
    SkillPublic,
    UserSkillAdd,
    UserSkillPublic,
    UserSkillUpdate,
)
from app.modules.users.models import User

router = APIRouter()


# ── Référentiel global ────────────────────────────────────

@router.get(
    "/",
    response_model=list[SkillPublic],
    summary="Lister toutes les compétences du référentiel",
)
async def list_skills(
    category: str | None = Query(default=None, description="Filtrer par catégorie"),
    search: str | None = Query(default=None, description="Recherche par nom"),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_skills(db, category=category, search=search)


@router.post(
    "/",
    response_model=SkillPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter une compétence au référentiel (admin uniquement)",
)
async def create_skill(
    data: SkillCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    return await service.create_skill(data, db)


# ── Compétences de l'utilisateur connecté ─────────────────

@router.get(
    "/me",
    response_model=list[UserSkillPublic],
    summary="Mes compétences",
)
async def my_skills(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_user_skills(current_user.id, db)


@router.post(
    "/me",
    response_model=UserSkillPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter une compétence à mon profil",
)
async def add_my_skill(
    data: UserSkillAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_skill = await service.add_user_skill(current_user.id, data, db)
    skills = await service.get_user_skills(current_user.id, db)
    return next(s for s in skills if s.skill_id == data.skill_id)


@router.put(
    "/me/{skill_id}",
    response_model=UserSkillPublic,
    summary="Modifier le niveau d'une compétence",
)
async def update_my_skill(
    skill_id: UUID,
    data: UserSkillUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await service.update_user_skill(current_user.id, skill_id, data, db)
    skills = await service.get_user_skills(current_user.id, db)
    return next(s for s in skills if s.skill_id == skill_id)


@router.delete(
    "/me/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une compétence de mon profil",
)
async def remove_my_skill(
    skill_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await service.remove_user_skill(current_user.id, skill_id, db)


# ── Compétences d'un autre utilisateur ────────────────────

@router.get(
    "/users/{user_id}",
    response_model=list[UserSkillPublic],
    summary="Voir les compétences d'un autre utilisateur",
)
async def user_skills(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await service.get_user_skills(user_id, db)


@router.post(
    "/users/{user_id}/validate/{skill_id}",
    response_model=UserSkillPublic,
    summary="Valider la compétence d'un pair",
)
async def validate_peer_skill(
    user_id: UUID,
    skill_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await service.validate_skill(user_id, skill_id, current_user.id, db)
    skills = await service.get_user_skills(user_id, db)
    return next(s for s in skills if s.skill_id == skill_id)
