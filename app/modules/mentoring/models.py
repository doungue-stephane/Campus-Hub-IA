import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MentoringPair(Base):
    __tablename__ = "mentoring_pairs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mentor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mentee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    match_score: Mapped[float | None] = mapped_column()
    status: Mapped[str] = mapped_column(
        String(20), default="active"
        # active | paused | completed
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relations
    sessions: Mapped[list["MentoringSession"]] = relationship(
        back_populates="pair", cascade="all, delete-orphan"
    )
    messages: Mapped[list["MentoringMessage"]] = relationship(
        back_populates="pair", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<MentoringPair mentor={self.mentor_id} mentee={self.mentee_id}>"


class MentoringSession(Base):
    __tablename__ = "mentoring_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pair_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mentoring_pairs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20), default="scheduled"
        # scheduled | done | cancelled
    )
    mentor_rating: Mapped[int | None] = mapped_column(Integer)   # 1-5
    mentee_rating: Mapped[int | None] = mapped_column(Integer)   # 1-5
    feedback_mentor: Mapped[str | None] = mapped_column(Text)
    feedback_mentee: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relations
    pair: Mapped["MentoringPair"] = relationship(back_populates="sessions")

    def __repr__(self) -> str:
        return f"<MentoringSession pair={self.pair_id} [{self.status}]>"


class MentoringMessage(Base):
    __tablename__ = "mentoring_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pair_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mentoring_pairs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relations
    pair: Mapped["MentoringPair"] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message pair={self.pair_id} sender={self.sender_id}>"
