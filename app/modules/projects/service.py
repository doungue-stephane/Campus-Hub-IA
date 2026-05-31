from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.matching import rank_projects_for_student, rank_students_for_project
from app.modules.projects.models import Project, ProjectApplication, ProjectMember
from app.modules.projects.schemas import (
    ApplicationStatusUpdate,
    ProjectCreate,
    ProjectMatchResult,
    ProjectUpdate,
    StudentMatchResult,
)
from app.modules.skills.models import UserSkill
from app.modules.users.models import User


# ── CRUD Projets ──────────────────────────────────────────

async def create_project(
    data: ProjectCreate, supervisor_id: UUID, db: AsyncSession
) -> Project:
    project = Project(
        title=data.title,
        description=data.description,
        required_skills=[s.model_dump() for s in data.required_skills],
        team_size_target=data.team_size_target,
        duration_weeks=data.duration_weeks,
        supervisor_id=supervisor_id,
        type=data.type,
    )
    db.add(project)
    await db.flush()
    return project


async def list_projects(
    db: AsyncSession,
    status_filter: str | None = None,
    type_filter: str | None = None,
) -> list[Project]:
    query = select(Project).order_by(Project.created_at.desc())
    if status_filter:
        query = query.where(Project.status == status_filter)
    if type_filter:
        query = query.where(Project.type == type_filter)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_project_or_404(project_id: UUID, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projet introuvable",
        )
    return project


async def update_project(
    project_id: UUID, data: ProjectUpdate, user: User, db: AsyncSession
) -> Project:
    project = await get_project_or_404(project_id, db)

    # Seul le superviseur ou un admin peut modifier
    if project.supervisor_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le superviseur du projet peut le modifier",
        )

    for field, value in data.model_dump(exclude_none=True).items():
        if field == "required_skills":
            value = [s if isinstance(s, dict) else s.model_dump() for s in value]
        setattr(project, field, value)

    return project


async def delete_project(
    project_id: UUID, user: User, db: AsyncSession
) -> None:
    project = await get_project_or_404(project_id, db)
    if project.supervisor_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le superviseur peut supprimer ce projet",
        )
    await db.delete(project)


# ── Matching ──────────────────────────────────────────────

async def _get_student_skills_payload(user_id: UUID, db: AsyncSession) -> list[dict]:
    """Récupère les compétences d'un étudiant au format attendu par le moteur IA."""
    result = await db.execute(
        select(UserSkill).where(UserSkill.user_id == user_id)
    )
    rows = result.scalars().all()
    return [{"skill_id": r.skill_id, "level": r.level} for r in rows]


async def get_matches_for_student(
    student_id: UUID, db: AsyncSession, top_k: int = 10
) -> list[ProjectMatchResult]:
    """Retourne les projets ouverts les mieux adaptés à l'étudiant."""
    student_skills = await _get_student_skills_payload(student_id, db)

    result = await db.execute(
        select(Project).where(Project.status == "open")
    )
    projects = result.scalars().all()

    projects_payload = [
        {
            "project_id": p.id,
            "required_skills": p.required_skills or [],
            "title": p.title,
            "description": p.description,
        }
        for p in projects
    ]

    ranked = rank_projects_for_student(student_skills, projects_payload, top_k)

    # Enrichir avec les infos du projet
    project_map = {p.id: p for p in projects}
    results = []
    for item in ranked:
        p = project_map[item["project_id"]]
        results.append(
            ProjectMatchResult(
                project_id=p.id,
                title=p.title,
                description=p.description,
                score=item["score"],
                score_percent=int(item["score"] * 100),
            )
        )
    return results


async def get_matches_for_project(
    project_id: UUID, db: AsyncSession, top_k: int = 20
) -> list[StudentMatchResult]:
    """Retourne les étudiants les mieux compatibles avec un projet."""
    project = await get_project_or_404(project_id, db)
    required_skills = project.required_skills or []

    # Récupère tous les étudiants actifs
    result = await db.execute(
        select(User).where(User.is_active == True, User.role == "student")
    )
    students = result.scalars().all()

    # Charge leurs compétences
    students_payload = []
    for student in students:
        skills = await _get_student_skills_payload(student.id, db)
        students_payload.append({"user_id": student.id, "skills": skills})

    ranked = rank_students_for_project(required_skills, students_payload, top_k)

    return [
        StudentMatchResult(
            user_id=item["user_id"],
            score=item["score"],
            score_percent=int(item["score"] * 100),
        )
        for item in ranked
    ]


# ── Candidatures ──────────────────────────────────────────

async def apply_to_project(
    project_id: UUID, student_id: UUID, db: AsyncSession
) -> ProjectApplication:
    project = await get_project_or_404(project_id, db)

    if project.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce projet n'accepte plus de candidatures",
        )

    # Déjà candidat ?
    existing = await db.execute(
        select(ProjectApplication).where(
            ProjectApplication.project_id == project_id,
            ProjectApplication.student_id == student_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tu as déjà postulé à ce projet",
        )

    # Calcule le score au moment de la candidature
    student_skills = await _get_student_skills_payload(student_id, db)
    from app.ai.matching import compute_match_score
    score = compute_match_score(student_skills, project.required_skills or [])

    application = ProjectApplication(
        project_id=project_id,
        student_id=student_id,
        match_score=score,
    )
    db.add(application)
    await db.flush()
    return application


async def update_application_status(
    project_id: UUID,
    application_id: UUID,
    data: ApplicationStatusUpdate,
    user: User,
    db: AsyncSession,
) -> ProjectApplication:
    project = await get_project_or_404(project_id, db)

    if project.supervisor_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le superviseur peut traiter les candidatures",
        )

    result = await db.execute(
        select(ProjectApplication).where(
            ProjectApplication.id == application_id,
            ProjectApplication.project_id == project_id,
        )
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidature introuvable",
        )

    application.status = data.status

    # Si accepté → ajouter comme membre
    if data.status == "accepted":
        existing_member = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == application.student_id,
            )
        )
        if not existing_member.scalar_one_or_none():
            db.add(ProjectMember(
                project_id=project_id,
                user_id=application.student_id,
                role="member",
            ))

    return application


async def get_project_members(
    project_id: UUID, db: AsyncSession
) -> list[ProjectMember]:
    await get_project_or_404(project_id, db)
    result = await db.execute(
        select(ProjectMember).where(ProjectMember.project_id == project_id)
    )
    return list(result.scalars().all())
