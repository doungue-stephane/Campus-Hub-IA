from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.events import service
from app.modules.events.schemas import (
    EventAnalytics,
    EventCreate,
    EventPublic,
    EventRecommendation,
    EventUpdate,
    FeedbackCreate,
    RegistrationPublic,
)
from app.modules.users.models import User

router = APIRouter()


# ── Événements ────────────────────────────────────────────

@router.get(
    "/",
    response_model=list[EventPublic],
    summary="Lister les événements",
)
async def list_events(
    status: str | None = Query(default=None, description="published | cancelled | draft"),
    tag: str | None = Query(default=None, description="Filtrer par tag"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await service.list_events(db, status_filter=status, tag=tag)


@router.post(
    "/",
    response_model=EventPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un événement",
)
async def create_event(
    data: EventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.create_event(data, current_user.id, db)


@router.get(
    "/recommended",
    response_model=list[EventRecommendation],
    summary="Événements recommandés pour moi par l'IA",
)
async def recommended_events(
    top_k: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.get_recommended_events(current_user, db, top_k)


@router.get(
    "/{event_id}",
    response_model=EventPublic,
    summary="Détail d'un événement",
)
async def get_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await service._get_event_or_404(event_id, db)


@router.put(
    "/{event_id}",
    response_model=EventPublic,
    summary="Modifier un événement",
)
async def update_event(
    event_id: UUID,
    data: EventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.update_event(event_id, data, current_user, db)


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un événement",
)
async def delete_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await service.delete_event(event_id, current_user, db)


# ── Inscriptions ──────────────────────────────────────────

@router.post(
    "/{event_id}/register",
    response_model=RegistrationPublic,
    status_code=status.HTTP_201_CREATED,
    summary="S'inscrire à un événement",
)
async def register(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.register_to_event(event_id, current_user.id, db)


@router.delete(
    "/{event_id}/register",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Se désinscrire d'un événement",
)
async def cancel_registration(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await service.cancel_registration(event_id, current_user.id, db)


@router.post(
    "/{event_id}/feedback",
    response_model=RegistrationPublic,
    summary="Laisser un feedback post-événement",
)
async def submit_feedback(
    event_id: UUID,
    data: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.submit_feedback(event_id, current_user.id, data, db)


# ── Analytics ─────────────────────────────────────────────

@router.get(
    "/{event_id}/analytics",
    response_model=EventAnalytics,
    summary="Analytics d'un événement (organisateur / admin)",
)
async def event_analytics(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.get_event_analytics(event_id, current_user, db)
