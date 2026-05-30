from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.modules.auth.router import router as auth_router
from app.modules.skills.router import router as skills_router


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

