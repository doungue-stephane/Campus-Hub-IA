from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.matching import compute_match_score
from app.modules.mentoring.models import MentoringMessage, MentoringPair, MentoringSession
from app.modules.mentoring.schemas import (
    MentorDashboard,
    MessageCreate,
    PairCreate,
    PairStatusUpdate,
    SessionCreate,
    SessionUpdate,
)
from app.modules.skills.models import UserSkill
from app.modules.users.models import User


# ── Utilitaire interne ────────────────────────────────────

async def _get_pair_or_404(pair_id: UUID, db: AsyncSession) -> MentoringPair:
    result = await db.execute(
        select(MentoringPair).where(MentoringPair.id == pair_id)
    )
    pair = result.scalar_one_or_none()
    if not pair:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paire de mentorat introuvable",
        )
    return pair


def _assert_pair_member(pair: MentoringPair, user_id: UUID) -> None:
    if pair.mentor_id != user_id and pair.mentee_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu n'es pas membre de cette paire de mentorat",
        )


# ── Matching mentor / mentoré ─────────────────────────────

async def get_mentor_suggestions(
    mentee_id: UUID, db: AsyncSession, top_k: int = 5
) -> list[dict]:
    """
    Suggère les meilleurs mentors M1 pour un mentoré B1.
    Utilise le même moteur de matching que TalentMatch.
    """
    # Compétences du mentoré
    result = await db.execute(
        select(UserSkill).where(UserSkill.user_id == mentee_id)
    )
    mentee_skills = [
        {"skill_id": r.skill_id, "level": r.level}
        for r in result.scalars().all()
    ]

    # Tous les mentors actifs
    result = await db.execute(
        select(User).where(
            User.role == "mentor",
            User.is_active == True,
        )
    )
    mentors = result.scalars().all()

    scored = []
    for mentor in mentors:
        result = await db.execute(
            select(UserSkill).where(UserSkill.user_id == mentor.id)
        )
        mentor_skills = [
            {"skill_id": r.skill_id, "level": r.level, "weight": 1.0}
            for r in result.scalars().all()
        ]
        score = compute_match_score(mentee_skills, mentor_skills)
        scored.append({
            "user_id": mentor.id,
            "first_name": mentor.first_name,
            "last_name": mentor.last_name,
            "specialty": mentor.specialty,
            "score": score,
            "score_percent": int(score * 100),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


# ── Paires ────────────────────────────────────────────────

async def create_pair(data: PairCreate, db: AsyncSession) -> MentoringPair:
    # Vérifier que la paire n'existe pas déjà
    existing = await db.execute(
        select(MentoringPair).where(
            MentoringPair.mentor_id == data.mentor_id,
            MentoringPair.mentee_id == data.mentee_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette paire de mentorat existe déjà",
        )

    # Calcul du score de compatibilité
    mentee_result = await db.execute(
        select(UserSkill).where(UserSkill.user_id == data.mentee_id)
    )
    mentee_skills = [
        {"skill_id": r.skill_id, "level": r.level}
        for r in mentee_result.scalars().all()
    ]
    mentor_result = await db.execute(
        select(UserSkill).where(UserSkill.user_id == data.mentor_id)
    )
    mentor_skills = [
        {"skill_id": r.skill_id, "level": r.level, "weight": 1.0}
        for r in mentor_result.scalars().all()
    ]
    score = compute_match_score(mentee_skills, mentor_skills)

    pair = MentoringPair(
        mentor_id=data.mentor_id,
        mentee_id=data.mentee_id,
        match_score=score,
    )
    db.add(pair)
    await db.flush()
    return pair


async def get_my_pairs(user_id: UUID, db: AsyncSession) -> list[MentoringPair]:
    result = await db.execute(
        select(MentoringPair).where(
            (MentoringPair.mentor_id == user_id) |
            (MentoringPair.mentee_id == user_id)
        ).order_by(MentoringPair.started_at.desc())
    )
    return list(result.scalars().all())


async def update_pair_status(
    pair_id: UUID, data: PairStatusUpdate, user_id: UUID, db: AsyncSession
) -> MentoringPair:
    pair = await _get_pair_or_404(pair_id, db)
    _assert_pair_member(pair, user_id)
    pair.status = data.status
    return pair


# ── Sessions ──────────────────────────────────────────────

async def create_session(
    data: SessionCreate, user_id: UUID, db: AsyncSession
) -> MentoringSession:
    pair = await _get_pair_or_404(data.pair_id, db)
    _assert_pair_member(pair, user_id)

    session = MentoringSession(
        pair_id=data.pair_id,
        scheduled_at=data.scheduled_at,
        duration_minutes=data.duration_minutes,
        notes=data.notes,
    )
    db.add(session)
    await db.flush()
    return session


async def get_pair_sessions(
    pair_id: UUID, user_id: UUID, db: AsyncSession
) -> list[MentoringSession]:
    pair = await _get_pair_or_404(pair_id, db)
    _assert_pair_member(pair, user_id)

    result = await db.execute(
        select(MentoringSession)
        .where(MentoringSession.pair_id == pair_id)
        .order_by(MentoringSession.scheduled_at.desc())
    )
    return list(result.scalars().all())


async def update_session(
    session_id: UUID, data: SessionUpdate, user_id: UUID, db: AsyncSession
) -> MentoringSession:
    result = await db.execute(
        select(MentoringSession).where(MentoringSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session introuvable",
        )

    pair = await _get_pair_or_404(session.pair_id, db)
    _assert_pair_member(pair, user_id)

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(session, field, value)

    return session


# ── Messages ──────────────────────────────────────────────

async def get_messages(
    pair_id: UUID, user_id: UUID, db: AsyncSession
) -> list[MentoringMessage]:
    pair = await _get_pair_or_404(pair_id, db)
    _assert_pair_member(pair, user_id)

    # Marquer les messages non lus comme lus
    result = await db.execute(
        select(MentoringMessage).where(
            MentoringMessage.pair_id == pair_id,
            MentoringMessage.sender_id != user_id,
            MentoringMessage.read_at == None,
        )
    )
    unread = result.scalars().all()
    for msg in unread:
        msg.read_at = datetime.now(timezone.utc)

    result = await db.execute(
        select(MentoringMessage)
        .where(MentoringMessage.pair_id == pair_id)
        .order_by(MentoringMessage.sent_at.asc())
    )
    return list(result.scalars().all())


async def send_message(
    pair_id: UUID, data: MessageCreate, sender_id: UUID, db: AsyncSession
) -> MentoringMessage:
    pair = await _get_pair_or_404(pair_id, db)
    _assert_pair_member(pair, sender_id)

    if pair.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible d'envoyer un message dans une paire inactive",
        )

    message = MentoringMessage(
        pair_id=pair_id,
        sender_id=sender_id,
        content=data.content,
    )
    db.add(message)
    await db.flush()
    return message


# ── Dashboard mentor ──────────────────────────────────────

async def get_mentor_dashboard(mentor_id: UUID, db: AsyncSession) -> MentorDashboard:
    # Toutes les paires
    result = await db.execute(
        select(MentoringPair).where(MentoringPair.mentor_id == mentor_id)
    )
    pairs = result.scalars().all()
    pair_ids = [p.id for p in pairs]

    active_pairs = sum(1 for p in pairs if p.status == "active")

    # Sessions
    total_sessions = 0
    sessions_done = 0
    ratings = []

    if pair_ids:
        result = await db.execute(
            select(MentoringSession).where(
                MentoringSession.pair_id.in_(pair_ids)
            )
        )
        sessions = result.scalars().all()
        total_sessions = len(sessions)
        sessions_done = sum(1 for s in sessions if s.status == "done")
        ratings = [
            s.mentee_rating for s in sessions
            if s.mentee_rating is not None
        ]

    average_rating = round(sum(ratings) / len(ratings), 2) if ratings else None

    return MentorDashboard(
        total_mentees=len(pairs),
        active_pairs=active_pairs,
        total_sessions=total_sessions,
        sessions_done=sessions_done,
        average_rating=average_rating,
    )
