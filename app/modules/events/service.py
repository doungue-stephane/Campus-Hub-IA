from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.events.models import Event, EventRegistration
from app.modules.events.schemas import (
    EventAnalytics,
    EventCreate,
    EventRecommendation,
    EventUpdate,
    FeedbackCreate,
)
from app.modules.users.models import User


# ── Utilitaires ───────────────────────────────────────────

async def _get_event_or_404(event_id: UUID, db: AsyncSession) -> Event:
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Événement introuvable",
        )
    return event


# ── CRUD Événements ───────────────────────────────────────

async def create_event(
    data: EventCreate, organizer_id: UUID, db: AsyncSession
) -> Event:
    event = Event(
        title=data.title,
        description=data.description,
        location=data.location,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        capacity=data.capacity,
        tags=data.tags,
        organizer_id=organizer_id,
        organizer_club_id=data.organizer_club_id,
    )
    db.add(event)
    await db.flush()
    return event


async def list_events(
    db: AsyncSession,
    status_filter: str | None = None,
    tag: str | None = None,
) -> list[Event]:
    query = select(Event).order_by(Event.starts_at.asc())
    if status_filter:
        query = query.where(Event.status == status_filter)
    if tag:
        # Filtre sur le tableau de tags PostgreSQL
        query = query.where(Event.tags.contains([tag]))
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_event(
    event_id: UUID, data: EventUpdate, user: User, db: AsyncSession
) -> Event:
    event = await _get_event_or_404(event_id, db)

    if event.organizer_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul l'organisateur peut modifier cet événement",
        )
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(event, field, value)
    return event


async def delete_event(
    event_id: UUID, user: User, db: AsyncSession
) -> None:
    event = await _get_event_or_404(event_id, db)
    if event.organizer_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul l'organisateur peut supprimer cet événement",
        )
    await db.delete(event)


# ── Recommandation IA ─────────────────────────────────────

async def get_recommended_events(
    user: User, db: AsyncSession, top_k: int = 10
) -> list[EventRecommendation]:
    """
    Recommande les événements les plus pertinents pour un utilisateur.

    Logique MVP :
    - On récupère les tags des événements publiés à venir
    - On calcule un score de pertinence basé sur :
        * la spécialité de l'utilisateur (50%)
        * la promotion de l'utilisateur (30%)
        * popularité (nombre d'inscrits) (20%)
    """
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(Event).where(
            Event.status == "published",
            Event.starts_at > now,
        ).order_by(Event.starts_at.asc())
    )
    events = result.scalars().all()

    scored = []
    for event in events:
        score = _compute_event_relevance(event, user)
        scored.append((event, score))

    scored.sort(key=lambda x: x[1], reverse=True)

    return [
        EventRecommendation(
            event_id=e.id,
            title=e.title,
            description=e.description,
            starts_at=e.starts_at,
            location=e.location,
            tags=e.tags,
            relevance_score=round(score, 4),
        )
        for e, score in scored[:top_k]
    ]


def _compute_event_relevance(event: Event, user: User) -> float:
    """
    Score de pertinence entre un événement et un utilisateur.
    Basé sur la correspondance des tags avec la spécialité/promotion.
    """
    if not event.tags:
        return 0.1  # score minimal pour les événements sans tag

    tags = [t.lower() for t in event.tags]
    score = 0.0

    # Correspondance spécialité (50%)
    if user.specialty and any(
        user.specialty.lower() in tag or tag in user.specialty.lower()
        for tag in tags
    ):
        score += 0.5

    # Correspondance promotion (30%)
    if user.promotion and any(
        user.promotion.lower() in tag
        for tag in tags
    ):
        score += 0.3

    # Bonus popularité (20%) — score fixe MVP, sera calculé dynamiquement en Phase 2
    score += 0.2

    return min(score, 1.0)


# ── Inscriptions ──────────────────────────────────────────

async def register_to_event(
    event_id: UUID, user_id: UUID, db: AsyncSession
) -> EventRegistration:
    event = await _get_event_or_404(event_id, db)

    if event.status != "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cet événement n'accepte plus d'inscriptions",
        )

    # Déjà inscrit ?
    existing = await db.execute(
        select(EventRegistration).where(
            EventRegistration.event_id == event_id,
            EventRegistration.user_id == user_id,
            EventRegistration.status != "cancelled",
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tu es déjà inscrit à cet événement",
        )

    # Vérifier la capacité
    reg_status = "registered"
    if event.capacity:
        count_result = await db.execute(
            select(EventRegistration).where(
                EventRegistration.event_id == event_id,
                EventRegistration.status == "registered",
            )
        )
        current_count = len(count_result.scalars().all())
        if current_count >= event.capacity:
            reg_status = "waitlist"

    registration = EventRegistration(
        event_id=event_id,
        user_id=user_id,
        status=reg_status,
    )
    db.add(registration)
    await db.flush()
    return registration


async def cancel_registration(
    event_id: UUID, user_id: UUID, db: AsyncSession
) -> None:
    result = await db.execute(
        select(EventRegistration).where(
            EventRegistration.event_id == event_id,
            EventRegistration.user_id == user_id,
            EventRegistration.status != "cancelled",
        )
    )
    registration = result.scalar_one_or_none()
    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inscription introuvable",
        )
    registration.status = "cancelled"

    # Promouvoir le premier de la liste d'attente
    waitlist_result = await db.execute(
        select(EventRegistration).where(
            EventRegistration.event_id == event_id,
            EventRegistration.status == "waitlist",
        ).order_by(EventRegistration.registered_at.asc()).limit(1)
    )
    next_in_line = waitlist_result.scalar_one_or_none()
    if next_in_line:
        next_in_line.status = "registered"


async def submit_feedback(
    event_id: UUID,
    user_id: UUID,
    data: FeedbackCreate,
    db: AsyncSession,
) -> EventRegistration:
    result = await db.execute(
        select(EventRegistration).where(
            EventRegistration.event_id == event_id,
            EventRegistration.user_id == user_id,
        )
    )
    registration = result.scalar_one_or_none()
    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tu dois être inscrit pour laisser un feedback",
        )
    if registration.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tu ne peux pas laisser un feedback après annulation",
        )

    registration.feedback_score = data.score
    registration.feedback_comment = data.comment
    return registration


# ── Analytics ─────────────────────────────────────────────

async def get_event_analytics(
    event_id: UUID, user: User, db: AsyncSession
) -> EventAnalytics:
    event = await _get_event_or_404(event_id, db)

    if event.organizer_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul l'organisateur peut voir les analytics",
        )

    result = await db.execute(
        select(EventRegistration).where(EventRegistration.event_id == event_id)
    )
    registrations = result.scalars().all()

    total_registered = sum(1 for r in registrations if r.status == "registered")
    total_cancelled = sum(1 for r in registrations if r.status == "cancelled")
    waitlist_count = sum(1 for r in registrations if r.status == "waitlist")

    fill_rate = None
    if event.capacity and event.capacity > 0:
        fill_rate = round(total_registered / event.capacity * 100, 1)

    scores = [r.feedback_score for r in registrations if r.feedback_score is not None]
    average_feedback = round(sum(scores) / len(scores), 2) if scores else None

    return EventAnalytics(
        event_id=event.id,
        title=event.title,
        capacity=event.capacity,
        total_registered=total_registered,
        total_cancelled=total_cancelled,
        waitlist_count=waitlist_count,
        fill_rate=fill_rate,
        average_feedback=average_feedback,
    )
