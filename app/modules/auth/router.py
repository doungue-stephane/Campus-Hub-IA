from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserPublic,
)
from app.modules.auth import service
from app.modules.users.models import User

router = APIRouter()


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un compte",
)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user = await service.register_user(data, db)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Se connecter — retourne access + refresh token",
)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await service.login_user(data, db)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renouveler les tokens via le refresh token",
)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    return await service.refresh_tokens(data.refresh_token, db)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Révoquer le refresh token",
)
async def logout(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    await service.logout_user(data.refresh_token, db)


@router.get(
    "/me",
    response_model=UserPublic,
    summary="Profil de l'utilisateur connecté",
)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
