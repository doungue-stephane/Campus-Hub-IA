from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.mentoring import service
from app.modules.mentoring.schemas import (
    MentorDashboard,
    MessageCreate,
    MessagePublic,
    PairCreate,
    PairPublic,
    PairStatusUpdate,
    SessionCreate,
    SessionPublic,
    SessionUpdate,
)
from app.modules.users.models import User

router = APIRouter()


# ── Suggestions ───────────────────────────────────────────

@router.get(
    "/suggestions",
    summary="Mentors recommandés pour moi par l'IA",
)
async def mentor_suggestions(
    top_k: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.get_mentor_suggestions(current_user.id, db, top_k)


# ── Paires ────────────────────────────────────────────────

@router.post(
    "/pairs",
    response_model=PairPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une paire mentor / mentoré",
)
async def create_pair(
    data: PairCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await service.create_pair(data, db)


@router.get(
    "/pairs/me",
    response_model=list[PairPublic],
    summary="Mes paires de mentorat actives",
)
async def my_pairs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.get_my_pairs(current_user.id, db)


@router.patch(
    "/pairs/{pair_id}",
    response_model=PairPublic,
    summary="Changer le statut d'une paire (active/paused/completed)",
)
async def update_pair(
    pair_id: UUID,
    data: PairStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.update_pair_status(pair_id, data, current_user.id, db)


# ── Sessions ──────────────────────────────────────────────

@router.post(
    "/sessions",
    response_model=SessionPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Planifier une session de mentorat",
)
async def create_session(
    data: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.create_session(data, current_user.id, db)


@router.get(
    "/pairs/{pair_id}/sessions",
    response_model=list[SessionPublic],
    summary="Sessions d'une paire",
)
async def pair_sessions(
    pair_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.get_pair_sessions(pair_id, current_user.id, db)


@router.patch(
    "/sessions/{session_id}",
    response_model=SessionPublic,
    summary="Mettre à jour une session (notes, statut, évaluation)",
)
async def update_session(
    session_id: UUID,
    data: SessionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.update_session(session_id, data, current_user.id, db)


# ── Messages ──────────────────────────────────────────────

@router.get(
    "/pairs/{pair_id}/messages",
    response_model=list[MessagePublic],
    summary="Historique de messages d'une paire",
)
async def get_messages(
    pair_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.get_messages(pair_id, current_user.id, db)


@router.post(
    "/pairs/{pair_id}/messages",
    response_model=MessagePublic,
    status_code=status.HTTP_201_CREATED,
    summary="Envoyer un message dans une paire",
)
async def send_message(
    pair_id: UUID,
    data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.send_message(pair_id, data, current_user.id, db)


# ── Dashboard ─────────────────────────────────────────────

@router.get(
    "/dashboard",
    response_model=MentorDashboard,
    summary="Tableau de bord du mentor",
)
async def mentor_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.get_mentor_dashboard(current_user.id, db)
