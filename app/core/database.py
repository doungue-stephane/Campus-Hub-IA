from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


# Moteur async
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,       # log les requêtes SQL en dev
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Factory de sessions
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# Classe de base pour tous les modèles SQLAlchemy
class Base(DeclarativeBase):
    pass


# Dépendance FastAPI — injectée dans les routes
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
