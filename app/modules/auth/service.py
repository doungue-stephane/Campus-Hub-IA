from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token_str,
    decode_token,
    hash_password,
    verify_password,
)
from app.modules.auth.schemas import LoginRequest, RegisterRequest, TokenResponse
from app.modules.users.models import RefreshToken, User
from jose import JWTError


async def register_user(data: RegisterRequest, db: AsyncSession) -> User:
    # Vérifier si l'email est déjà pris
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un compte avec cet email existe déjà",
        )

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        role=data.role,
        promotion=data.promotion,
        specialty=data.specialty,
    )
    db.add(user)
    await db.flush()   # génère l'ID sans committer
    return user


async def login_user(data: LoginRequest, db: AsyncSession) -> TokenResponse:
    # Récupérer l'utilisateur
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé",
        )

    return await _generate_tokens(user, db)


async def refresh_tokens(refresh_token_str: str, db: AsyncSession) -> TokenResponse:
    # Décoder le refresh token
    try:
        payload = decode_token(refresh_token_str)
        if payload.get("type") != "refresh":
            raise ValueError
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalide",
        )

    # Vérifier en BDD
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == refresh_token_str)
    )
    db_token = result.scalar_one_or_none()

    if not db_token or db_token.revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token révoqué ou introuvable",
        )

    if db_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expiré",
        )

    # Révoquer l'ancien token (rotation)
    db_token.revoked = True

    # Récupérer l'utilisateur
    result = await db.execute(select(User).where(User.id == db_token.user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur introuvable")

    return await _generate_tokens(user, db)


async def logout_user(refresh_token_str: str, db: AsyncSession) -> None:
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == refresh_token_str)
    )
    db_token = result.scalar_one_or_none()
    if db_token:
        db_token.revoked = True


# ── Utilitaire interne ────────────────────────────────────

async def _generate_tokens(user: User, db: AsyncSession) -> TokenResponse:
    access = create_access_token(subject=str(user.id), role=user.role)
    refresh_str, expires_at = create_refresh_token_str(subject=str(user.id))

    db_refresh = RefreshToken(
        user_id=user.id,
        token=refresh_str,
        expires_at=expires_at,
    )
    db.add(db_refresh)

    return TokenResponse(access_token=access, refresh_token=refresh_str)
