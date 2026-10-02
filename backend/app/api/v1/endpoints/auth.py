"""Authentication endpoints: Google OAuth only, /me, logout."""
from datetime import datetime, timezone
from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
)
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Auth"])
bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class GoogleAuthRequest(BaseModel):
    credential: str


class UserProfile(BaseModel):
    id: uuid.UUID
    google_id: str | None = None
    email: str
    name: str
    picture: str | None = None
    profile_picture_url: str | None = None
    onboarding_completed: bool = False
    onboarding_step: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None
    @property
    def first_name(self) -> str:
        return self.name.split()[0] if self.name else "there"

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_user(cls, user: User) -> "UserProfile":
        return cls(
            id=user.id,
            google_id=user.google_id,
            email=user.email,
            name=user.name,
            picture=user.profile_picture_url,
            profile_picture_url=user.profile_picture_url,
            onboarding_completed=user.onboarding_completed,
            onboarding_step=user.onboarding_step,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login_at=user.last_login_at,
        )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _verify_google_credential(credential: str) -> dict:
    """Verify Google ID token and return claims."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured on this server. Set GOOGLE_CLIENT_ID.",
        )

    try:
        id_info = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google credential: {exc}",
        ) from exc

    google_id = id_info.get("sub")
    email = id_info.get("email")
    name = id_info.get("name") or (email.split("@")[0] if email else "User")
    picture = id_info.get("picture")

    if not google_id or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google ID token missing sub or email claims",
        )

    return {
        "google_id": google_id,
        "email": email,
        "name": name,
        "picture": picture,
    }


async def _get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserProfile:
    """Extract and validate the Aptly JWT from the Authorization header and load DB user."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(credentials.credentials)
    if payload is None or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user identifier in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return UserProfile.from_orm_user(user)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/google/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def google_signup(
    body: GoogleAuthRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Sign up a NEW user via Google OAuth.
    If a user already exists with this Google ID or email, reject with 409 Conflict.
    """
    claims = _verify_google_credential(body.credential)
    google_id = claims["google_id"]
    email = claims["email"]
    name = claims["name"]
    picture = claims["picture"]

    # Check whether user already exists
    stmt = select(User).where((User.google_id == google_id) | (User.email == email))
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an Aptly account. Sign in instead.",
        )

    now = datetime.now(timezone.utc)
    new_user = User(
        id=uuid.uuid4(),
        google_id=google_id,
        email=email,
        name=name,
        profile_picture_url=picture,
        onboarding_completed=False,
        onboarding_step=1,
        last_login_at=now,
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)

    token = create_access_token(
        data={
            "sub": str(new_user.id),
            "email": new_user.email,
            "name": new_user.name,
        }
    )

    return TokenResponse(
        access_token=token,
        user=UserProfile.from_orm_user(new_user),
    )


@router.post("/google/login", response_model=TokenResponse)
async def google_login(
    body: GoogleAuthRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Sign in an EXISTING user via Google OAuth.
    If no user exists with this Google ID or email, reject with 404 Not Found.
    """
    claims = _verify_google_credential(body.credential)
    google_id = claims["google_id"]
    email = claims["email"]
    name = claims["name"]
    picture = claims["picture"]

    stmt = select(User).where((User.google_id == google_id) | (User.email == email))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Aptly account found. Create one first.",
        )

    now = datetime.now(timezone.utc)
    user.google_id = google_id
    user.email = email
    user.name = name
    user.profile_picture_url = picture
    user.last_login_at = now

    await db.flush()
    await db.refresh(user)

    token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "name": user.name,
        }
    )

    return TokenResponse(
        access_token=token,
        user=UserProfile.from_orm_user(user),
    )


@router.post("/google", response_model=TokenResponse)
async def google_auth(
    body: GoogleAuthRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Fallback general Google auth endpoint for existing clients.
    Defaults to login behavior for existing users, or creates new user.
    """
    claims = _verify_google_credential(body.credential)
    google_id = claims["google_id"]
    email = claims["email"]
    name = claims["name"]
    picture = claims["picture"]

    now = datetime.now(timezone.utc)
    stmt = select(User).where((User.google_id == google_id) | (User.email == email))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        user.google_id = google_id
        user.email = email
        user.name = name
        user.profile_picture_url = picture
        user.last_login_at = now
    else:
        user = User(
            id=uuid.uuid4(),
            google_id=google_id,
            email=email,
            name=name,
            profile_picture_url=picture,
            onboarding_completed=False,
            onboarding_step=1,
            last_login_at=now,
        )
        db.add(user)

    await db.flush()
    await db.refresh(user)

    token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "name": user.name,
        }
    )

    return TokenResponse(
        access_token=token,
        user=UserProfile.from_orm_user(user),
    )


@router.get("/me", response_model=UserProfile)
async def get_me(
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
) -> UserProfile:
    """Return the currently authenticated user's profile from the database."""
    return current_user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    _: Annotated[UserProfile, Depends(_get_current_user)],
) -> None:
    """
    Logout endpoint. JWTs are stateless; the client must discard the token.
    Returns 204 No Content to confirm the action was received.
    """
    return None
