from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ── Hashing des mots de passe ─────────────────────────────
# bcrypt limite le mot de passe à 72 octets. bcrypt_sha256 contourne cette limite
# en hachant d'abord le mot de passe avec SHA256 avant d'utiliser bcrypt.
pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── Tokens JWT ────────────────────────────────────────────
def create_access_token(subject: str, role: str) -> str:
    """Génère un access token (courte durée)."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload: dict[str, Any] = {
        "sub": subject,       # user_id en string
        "role": role,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token_str(subject: str) -> tuple[str, datetime]:
    """
    Génère un refresh token (longue durée).
    Retourne (token_str, expires_at).
    """
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "type": "refresh",
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, expire


def decode_token(token: str) -> dict[str, Any]:
    """Décode et valide un token. Lève JWTError si invalide."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except JWTError:
        raise
