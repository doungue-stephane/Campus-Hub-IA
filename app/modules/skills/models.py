import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Skill(Base):
    """Référentiel global des compétences."""
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
        # technical | soft | language | certification
    )
    taxonomy_ref: Mapped[str | None] = mapped_column(String(50))  # code ROME / ESCO

    # Relation inverse
    user_skills: Mapped[list["UserSkill"]] = relationship(back_populates="skill")

    def __repr__(self) -> str:
        return f"<Skill {self.name} [{self.category}]>"


class UserSkill(Base):
    """Compétences rattachées à un étudiant."""
    __tablename__ = "user_skills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
    )
    level: Mapped[str] = mapped_column(
        String(20), nullable=False
        # beginner | intermediate | advanced | expert
    )
    validated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relations
    skill: Mapped["Skill"] = relationship(back_populates="user_skills")

    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", name="uq_user_skill"),
    )

    def __repr__(self) -> str:
        return f"<UserSkill user={self.user_id} skill={self.skill_id} [{self.level}]>"
