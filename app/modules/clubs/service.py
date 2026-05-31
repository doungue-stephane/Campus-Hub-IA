from uuid import UUID
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.clubs.models import Club, ClubMember, ClubOffer
from app.modules.clubs.schemas import (
    ClubBenchmark,
    ClubCreate,
    ClubKPIs,
    ClubOfferCreate,
    ClubOfferUpdate,
    ClubUpdate,
)
from app.modules.users.models import User


# ── Utilitaires ───────────────────────────────────────────

async def _get_club_or_404(club_id: UUID, db: AsyncSession) -> Club:
    result = await db.execute(select(Club).where(Club.id == club_id))
    club = result.scalar_one_or_none()
    if not club:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Club introuvable",
        )
    return club


def _assert_manager(club: Club, user: User) -> None:
    if club.manager_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le responsable du club peut effectuer cette action",
        )


# ── CRUD Clubs ────────────────────────────────────────────

async def create_club(data: ClubCreate, db: AsyncSession) -> Club:
    result = await db.execute(select(Club).where(Club.name == data.name))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Un club nommé '{data.name}' existe déjà",
        )
    club = Club(**data.model_dump())
    db.add(club)
    await db.flush()
    return club


async def list_clubs(db: AsyncSession) -> list[Club]:
    result = await db.execute(select(Club).order_by(Club.name))
    return list(result.scalars().all())


async def update_club(
    club_id: UUID, data: ClubUpdate, user: User, db: AsyncSession
) -> Club:
    club = await _get_club_or_404(club_id, db)
    _assert_manager(club, user)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(club, field, value)
    return club


async def delete_club(club_id: UUID, user: User, db: AsyncSession) -> None:
    club = await _get_club_or_404(club_id, db)
    _assert_manager(club, user)
    await db.delete(club)


# ── Membres ───────────────────────────────────────────────

async def join_club(club_id: UUID, user_id: UUID, db: AsyncSession) -> ClubMember:
    await _get_club_or_404(club_id, db)

    # Déjà membre actif ?
    existing = await db.execute(
        select(ClubMember).where(
            ClubMember.club_id == club_id,
            ClubMember.user_id == user_id,
            ClubMember.left_at == None,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tu es déjà membre de ce club",
        )

    member = ClubMember(club_id=club_id, user_id=user_id)
    db.add(member)
    await db.flush()
    return member


async def leave_club(club_id: UUID, user_id: UUID, db: AsyncSession) -> None:
    result = await db.execute(
        select(ClubMember).where(
            ClubMember.club_id == club_id,
            ClubMember.user_id == user_id,
            ClubMember.left_at == None,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tu n'es pas membre actif de ce club",
        )
    member.left_at = datetime.now(timezone.utc)


async def remove_member(
    club_id: UUID, user_id: UUID, manager: User, db: AsyncSession
) -> None:
    club = await _get_club_or_404(club_id, db)
    _assert_manager(club, manager)

    result = await db.execute(
        select(ClubMember).where(
            ClubMember.club_id == club_id,
            ClubMember.user_id == user_id,
            ClubMember.left_at == None,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membre introuvable",
        )
    member.left_at = datetime.now(timezone.utc)


async def get_club_members(club_id: UUID, db: AsyncSession) -> list[ClubMember]:
    await _get_club_or_404(club_id, db)
    result = await db.execute(
        select(ClubMember)
        .where(ClubMember.club_id == club_id, ClubMember.left_at == None)
        .order_by(ClubMember.joined_at.desc())
    )
    return list(result.scalars().all())


# ── Offres ────────────────────────────────────────────────

async def create_offer(
    club_id: UUID, data: ClubOfferCreate, user: User, db: AsyncSession
) -> ClubOffer:
    club = await _get_club_or_404(club_id, db)
    _assert_manager(club, user)
    offer = ClubOffer(club_id=club_id, **data.model_dump())
    db.add(offer)
    await db.flush()
    return offer


async def list_offers(club_id: UUID, db: AsyncSession) -> list[ClubOffer]:
    await _get_club_or_404(club_id, db)
    result = await db.execute(
        select(ClubOffer)
        .where(ClubOffer.club_id == club_id)
        .order_by(ClubOffer.created_at.desc())
    )
    return list(result.scalars().all())


async def update_offer(
    offer_id: UUID, data: ClubOfferUpdate, user: User, db: AsyncSession
) -> ClubOffer:
    result = await db.execute(select(ClubOffer).where(ClubOffer.id == offer_id))
    offer = result.scalar_one_or_none()
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offre introuvable")

    club = await _get_club_or_404(offer.club_id, db)
    _assert_manager(club, user)

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(offer, field, value)
    return offer


# ── KPIs ──────────────────────────────────────────────────

async def get_club_kpis(club_id: UUID, db: AsyncSession) -> ClubKPIs:
    club = await _get_club_or_404(club_id, db)

    # Membres
    all_members_result = await db.execute(
        select(ClubMember).where(ClubMember.club_id == club_id)
    )
    all_members = all_members_result.scalars().all()
    total_members = len(all_members)
    active_members = sum(1 for m in all_members if m.left_at is None)
    retention_rate = round(active_members / total_members * 100, 1) if total_members else 0.0

    # Offres
    offers_result = await db.execute(
        select(ClubOffer).where(ClubOffer.club_id == club_id)
    )
    offers = offers_result.scalars().all()
    total_offers = len(offers)
    open_offers = sum(1 for o in offers if o.status == "open")

    return ClubKPIs(
        club_id=club.id,
        club_name=club.name,
        total_members=total_members,
        active_members=active_members,
        retention_rate=retention_rate,
        total_offers=total_offers,
        open_offers=open_offers,
    )


async def get_benchmark(db: AsyncSession) -> list[ClubBenchmark]:
    """Benchmark anonymisé inter-clubs trié par membres actifs."""
    result = await db.execute(select(Club).order_by(Club.name))
    clubs = result.scalars().all()

    benchmarks = []
    for club in clubs:
        kpis = await get_club_kpis(club.id, db)
        benchmarks.append(
            ClubBenchmark(
                rank=0,  # calculé après tri
                club_id=club.id,
                club_name=club.name,
                total_members=kpis.total_members,
                active_members=kpis.active_members,
                open_offers=kpis.open_offers,
            )
        )

    benchmarks.sort(key=lambda x: x.active_members, reverse=True)
    for i, b in enumerate(benchmarks):
        b.rank = i + 1

    return benchmarks
