"""
Moteur de matching TalentMatch — Phase 1 MVP

Logique :
- Chaque compétence est encodée avec un poids selon le niveau.
- On calcule la similarité cosinus entre le vecteur étudiant
  et le vecteur projet.
- Score final pondéré : compétences 60 %, bonus niveau 40 %.

Phase 2 : on ajoutera les embeddings sémantiques Sentence-BERT
sur les descriptions textuelles.
"""

from uuid import UUID
import math


# Poids numériques par niveau de compétence
LEVEL_WEIGHTS: dict[str, float] = {
    "beginner": 0.25,
    "intermediate": 0.50,
    "advanced": 0.75,
    "expert": 1.00,
}


def _cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    """
    Calcule la similarité cosinus entre deux vecteurs sparse
    représentés comme des dicts {skill_id: weight}.
    Retourne un score entre 0.0 et 1.0.
    """
    # Produit scalaire
    dot = sum(vec_a.get(k, 0.0) * vec_b.get(k, 0.0) for k in vec_b)

    # Normes
    norm_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
    norm_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def build_student_vector(user_skills: list[dict]) -> dict[str, float]:
    """
    Construit le vecteur de compétences d'un étudiant.
    user_skills : liste de {"skill_id": UUID, "level": str}
    """
    return {
        str(s["skill_id"]): LEVEL_WEIGHTS.get(s["level"], 0.0)
        for s in user_skills
    }


def build_project_vector(required_skills: list[dict]) -> dict[str, float]:
    """
    Construit le vecteur de compétences requises par un projet.
    required_skills : liste de {"skill_id": UUID, "level": str, "weight": float}
    Le champ 'weight' est le coefficient d'importance (0.0 → 1.0).
    """
    vec = {}
    for s in required_skills:
        level_score = LEVEL_WEIGHTS.get(s.get("level", "beginner"), 0.25)
        importance = float(s.get("weight", 1.0))
        vec[str(s["skill_id"])] = level_score * importance
    return vec


def compute_match_score(
    student_skills: list[dict],
    required_skills: list[dict],
) -> float:
    """
    Calcule le score de compatibilité entre un étudiant et un projet.
    Retourne un float entre 0.0 et 1.0.

    Formule :
      - similarité cosinus sur les vecteurs de compétences
      - bonus si l'étudiant couvre toutes les compétences requises
    """
    if not required_skills:
        return 0.0

    student_vec = build_student_vector(student_skills)
    project_vec = build_project_vector(required_skills)

    cosine_score = _cosine_similarity(student_vec, project_vec)

    # Bonus de couverture : % des compétences requises présentes dans le profil
    required_ids = {str(s["skill_id"]) for s in required_skills}
    student_ids = set(student_vec.keys())
    coverage = len(required_ids & student_ids) / len(required_ids)

    # Score final : 60% similarité cosinus + 40% couverture
    final_score = (cosine_score * 0.6) + (coverage * 0.4)

    return round(min(final_score, 1.0), 4)


def rank_students_for_project(
    required_skills: list[dict],
    students: list[dict],
    top_k: int = 20,
) -> list[dict]:
    """
    Classe les étudiants par score décroissant pour un projet donné.

    students : liste de {"user_id": UUID, "skills": [...]}
    Retourne : liste de {"user_id": UUID, "score": float} triée
    """
    scored = []
    for student in students:
        score = compute_match_score(
            student_skills=student["skills"],
            required_skills=required_skills,
        )
        scored.append({"user_id": student["user_id"], "score": score})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def rank_projects_for_student(
    student_skills: list[dict],
    projects: list[dict],
    top_k: int = 10,
) -> list[dict]:
    """
    Classe les projets par score décroissant pour un étudiant donné.

    projects : liste de {"project_id": UUID, "required_skills": [...]}
    Retourne : liste de {"project_id": UUID, "score": float} triée
    """
    scored = []
    for project in projects:
        score = compute_match_score(
            student_skills=student_skills,
            required_skills=project["required_skills"] or [],
        )
        scored.append({"project_id": project["project_id"], "score": score})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]
