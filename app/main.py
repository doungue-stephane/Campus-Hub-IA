from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.modules.auth.router import router as auth_router
from app.modules.projects.router import router as projects_router
from app.modules.skills.router import router as skills_router
from app.modules.mentoring.router import router as mentoring_router
from app.modules.clubs.router import router as clubs_router
from app.modules.events.router import router as events_router




app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Plateforme intelligente de matching compétences – projets – clubs – mentorat – événements",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS — à restreindre en production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else ["https://campushub.fr"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health check ──────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


# ── Routers ───────────────────────────────────────────────
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(skills_router, prefix="/skills", tags=["Skills"])
app.include_router(projects_router, prefix="/projects", tags=["Projects"])
app.include_router(mentoring_router, prefix="/mentoring", tags=["Mentoring"])
app.include_router(events_router,    prefix="/events",    tags=["Events"])
app.include_router(clubs_router, prefix="/clubs", tags=["Clubs"])