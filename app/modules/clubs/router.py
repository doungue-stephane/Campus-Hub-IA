from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.modules.clubs import service
from app.modules.clubs.schemas import (
    ClubBenchmark,
    ClubCreate,
    ClubKPIs,
    ClubMemberPublic,
    ClubOfferCreate,
    ClubOfferPublic,
    ClubOfferUpdate,
    ClubPublic,
    ClubUpdate,
)
from app.modules.users.models import User

router = APIRouter()


# ── Clubs ─────────────────────────────────────────────────

@router.get(
    "/",
    response_model=list[ClubPublic],
    summary="Lister tous les clubs",
)
async def list_clubs(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await service.list_clubs(db)


@router.post(
    "/",
    response_model=ClubPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un club (admin uniquement)",
)
async def create_club(
    data: ClubCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    return await service.create_club(data, db)


@router.get(
    "/benchmark",
    response_model=list[ClubBenchmark],
    summary="Benchmark inter-clubs (tous les clubs classés)",
)
async def benchmark(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await service.get_benchmark(db)


@router.get(
    "/{club_id}",
    response_model=ClubPublic,
    summary="Détail d'un club",
)
async def get_club(
    club_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await service._get_club_or_404(club_id, db)


@router.put(
    "/{club_id}",
    response_model=ClubPublic,
    summary="Modifier un club",
)
async def update_club(
    club_id: UUID,
    data: ClubUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.update_club(club_id, data, current_user, db)


@router.delete(
    "/{club_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un club (admin ou manager)",
)
async def delete_club(
    club_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await service.delete_club(club_id, current_user, db)


# ── Membres ───────────────────────────────────────────────

@router.get(
    "/{club_id}/members",
    response_model=list[ClubMemberPublic],
    summary="Membres actifs d'un club",
)
async def club_members(
    club_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await service.get_club_members(club_id, db)


@router.post(
    "/{club_id}/join",
    response_model=ClubMemberPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Rejoindre un club",
)
async def join_club(
    club_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.join_club(club_id, current_user.id, db)


@router.post(
    "/{club_id}/leave",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Quitter un club",
)
async def leave_club(
    club_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await service.leave_club(club_id, current_user.id, db)


@router.delete(
    "/{club_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Retirer un membre (manager ou admin)",
)
async def remove_member(
    club_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await service.remove_member(club_id, user_id, current_user, db)


# ── KPIs ──────────────────────────────────────────────────

@router.get(
    "/{club_id}/kpis",
    response_model=ClubKPIs,
    summary="KPIs d'un club (membres, rétention, offres)",
)
async def club_kpis(
    club_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await service.get_club_kpis(club_id, db)


# ── Offres ────────────────────────────────────────────────

@router.get(
    "/{club_id}/offers",
    response_model=list[ClubOfferPublic],
    summary="Offres de bénévolat d'un club",
)
async def list_offers(
    club_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await service.list_offers(club_id, db)


@router.post(
    "/{club_id}/offers",
    response_model=ClubOfferPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Publier une offre de bénévolat",
)
async def create_offer(
    club_id: UUID,
    data: ClubOfferCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.create_offer(club_id, data, current_user, db)


@router.patch(
    "/{club_id}/offers/{offer_id}",
    response_model=ClubOfferPublic,
    summary="Modifier une offre",
)
async def update_offer(
    club_id: UUID,
    offer_id: UUID,
    data: ClubOfferUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.update_offer(offer_id, data, current_user, db)
