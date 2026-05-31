from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.modules.projects import service
from app.modules.projects.schemas import (
    ApplicationPublic,
    ApplicationStatusUpdate,
    ProjectCreate,
    ProjectMatchResult,
    ProjectMemberPublic,
    ProjectPublic,
    ProjectUpdate,
    StudentMatchResult,
)
from app.modules.users.models import User

router = APIRouter()


# ── CRUD Projets ──────────────────────────────────────────

@router.post(
    "/",
    response_model=ProjectPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un projet",
)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.create_project(data, current_user.id, db)


@router.get(
    "/",
    response_model=list[ProjectPublic],
    summary="Lister les projets",
)
async def list_projects(
    status: str | None = Query(default=None, description="open | in_progress | closed"),
    type: str | None = Query(default=None, description="open_innovation | personal | club"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await service.list_projects(db, status_filter=status, type_filter=type)


@router.get(
    "/my-matches",
    response_model=list[ProjectMatchResult],
    summary="Projets recommandés pour moi par l'IA",
)
async def my_project_matches(
    top_k: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.get_matches_for_student(current_user.id, db, top_k)


@router.get(
    "/{project_id}",
    response_model=ProjectPublic,
    summary="Détail d'un projet",
)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await service.get_project_or_404(project_id, db)


@router.put(
    "/{project_id}",
    response_model=ProjectPublic,
    summary="Modifier un projet",
)
async def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.update_project(project_id, data, current_user, db)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un projet",
)
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await service.delete_project(project_id, current_user, db)


# ── Matching ──────────────────────────────────────────────

@router.get(
    "/{project_id}/matches",
    response_model=list[StudentMatchResult],
    summary="Top étudiants recommandés pour ce projet",
)
async def project_student_matches(
    project_id: UUID,
    top_k: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await service.get_matches_for_project(project_id, db, top_k)


# ── Candidatures ──────────────────────────────────────────

@router.post(
    "/{project_id}/apply",
    response_model=ApplicationPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Postuler à un projet",
)
async def apply(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.apply_to_project(project_id, current_user.id, db)


@router.put(
    "/{project_id}/applications/{application_id}",
    response_model=ApplicationPublic,
    summary="Accepter ou refuser une candidature",
)
async def update_application(
    project_id: UUID,
    application_id: UUID,
    data: ApplicationStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.update_application_status(
        project_id, application_id, data, current_user, db
    )


# ── Membres ───────────────────────────────────────────────

@router.get(
    "/{project_id}/members",
    response_model=list[ProjectMemberPublic],
    summary="Membres actuels du projet",
)
async def project_members(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await service.get_project_members(project_id, db)
