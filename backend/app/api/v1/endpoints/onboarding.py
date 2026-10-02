"""Onboarding preferences endpoints."""
from datetime import datetime, timezone
from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import UserProfile, _get_current_user
from app.db.session import get_db
from app.models.preference import UserPreference
from app.models.user import User

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class UserPreferencesResponse(BaseModel):
    user_type: str | None = None
    opportunity_type: str | None = None
    graduation_year: int | None = None
    preferred_location: str | None = None
    preferred_roles: list[str] = []
    interests: list[str] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class UserPreferencesUpdate(BaseModel):
    user_type: str | None = None
    opportunity_type: str | None = None
    graduation_year: int | None = None
    preferred_location: str | None = None
    preferred_roles: list[str] = []
    interests: list[str] = []


ALLOWED_FREQUENCIES = {"daily", "important_only", "weekly"}


class PersonalizationResponse(BaseModel):
    focus_opportunity_matching: bool = True
    focus_resume_tailoring: bool = True
    focus_deadline_tracking: bool = True
    update_frequency: str = "daily"
    additional_notes: str | None = None
    onboarding_step: int = 3
    onboarding_completed: bool = False

    model_config = ConfigDict(from_attributes=True)


class PersonalizationUpdate(BaseModel):
    focus_opportunity_matching: bool = True
    focus_resume_tailoring: bool = True
    focus_deadline_tracking: bool = True
    update_frequency: str = Field(default="daily", description="daily | important_only | weekly")
    additional_notes: str | None = Field(default=None, max_length=300)

    @field_validator("update_frequency")
    @classmethod
    def validate_frequency(cls, v: str) -> str:
        if v == "important":
            v = "important_only"
        if v not in ALLOWED_FREQUENCIES:
            raise ValueError(f"Invalid update_frequency '{v}'. Allowed values: {', '.join(sorted(ALLOWED_FREQUENCIES))}")
        return v

    @field_validator("additional_notes")
    @classmethod
    def validate_notes(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 300:
            raise ValueError("additional_notes cannot exceed 300 characters")
        return v


class OnboardingStepUpdate(BaseModel):
    step: int | None = None
    completed: bool | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_preferences(
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserPreferencesResponse:
    """Retrieve the current user's onboarding preferences."""
    stmt = select(UserPreference).where(UserPreference.user_id == current_user.id)
    result = await db.execute(stmt)
    pref = result.scalar_one_or_none()

    if not pref:
        return UserPreferencesResponse()

    return UserPreferencesResponse(
        user_type=pref.user_type,
        opportunity_type=pref.opportunity_type,
        graduation_year=pref.graduation_year,
        preferred_location=pref.preferred_location,
        preferred_roles=pref.preferred_roles or [],
        interests=pref.interests or [],
        created_at=pref.created_at,
        updated_at=pref.updated_at,
    )


@router.put("/preferences", response_model=UserPreferencesResponse)
async def update_preferences(
    body: UserPreferencesUpdate,
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserPreferencesResponse:
    """Create or update the current user's onboarding preferences."""
    stmt = select(UserPreference).where(UserPreference.user_id == current_user.id)
    result = await db.execute(stmt)
    pref = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if not pref:
        pref = UserPreference(
            id=uuid.uuid4(),
            user_id=current_user.id,
            user_type=body.user_type,
            opportunity_type=body.opportunity_type,
            graduation_year=body.graduation_year,
            preferred_location=body.preferred_location,
            preferred_roles=body.preferred_roles,
            interests=body.interests,
            created_at=now,
            updated_at=now,
        )
        db.add(pref)
    else:
        pref.user_type = body.user_type
        pref.opportunity_type = body.opportunity_type
        pref.graduation_year = body.graduation_year
        pref.preferred_location = body.preferred_location
        pref.preferred_roles = body.preferred_roles
        pref.interests = body.interests
        pref.updated_at = now

    # Also ensure user onboarding_step is advanced to at least 2
    user_stmt = select(User).where(User.id == current_user.id)
    user_res = await db.execute(user_stmt)
    user = user_res.scalar_one_or_none()
    if user and user.onboarding_step < 2:
        user.onboarding_step = 2

    await db.flush()
    await db.refresh(pref)

    return UserPreferencesResponse(
        user_type=pref.user_type,
        opportunity_type=pref.opportunity_type,
        graduation_year=pref.graduation_year,
        preferred_location=pref.preferred_location,
        preferred_roles=pref.preferred_roles or [],
        interests=pref.interests or [],
        created_at=pref.created_at,
        updated_at=pref.updated_at,
    )


@router.put("/step", response_model=UserProfile)
@router.patch("/step", response_model=UserProfile)
async def update_onboarding_step(
    body: OnboardingStepUpdate,
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserProfile:
    """Update current user's onboarding step and completion status."""
    stmt = select(User).where(User.id == current_user.id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if body.step is not None:
        user.onboarding_step = max(1, min(body.step, 4))
    if body.completed is not None:
        user.onboarding_completed = body.completed
        if body.completed:
            user.onboarding_step = 4

    await db.flush()
    await db.refresh(user)

    return UserProfile.from_orm_user(user)


@router.post("/complete", response_model=UserProfile)
async def complete_onboarding(
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserProfile:
    """Mark onboarding as complete and advance step to 4."""
    stmt = select(User).where(User.id == current_user.id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.onboarding_completed = True
    user.onboarding_step = 4

    await db.flush()
    await db.refresh(user)

    return UserProfile.from_orm_user(user)


@router.get("/personalization", response_model=PersonalizationResponse)
async def get_personalization(
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PersonalizationResponse:
    """Retrieve the current user's AI copilot personalization preferences."""
    stmt = select(UserPreference).where(UserPreference.user_id == current_user.id)
    result = await db.execute(stmt)
    pref = result.scalar_one_or_none()

    # Load latest user record for current onboarding_step and onboarding_completed status
    user_stmt = select(User).where(User.id == current_user.id)
    user_res = await db.execute(user_stmt)
    user = user_res.scalar_one_or_none()

    step = user.onboarding_step if user else current_user.onboarding_step
    completed = user.onboarding_completed if user else current_user.onboarding_completed

    if not pref:
        return PersonalizationResponse(
            focus_opportunity_matching=True,
            focus_resume_tailoring=True,
            focus_deadline_tracking=True,
            update_frequency="daily",
            additional_notes=None,
            onboarding_step=step,
            onboarding_completed=completed,
        )

    return PersonalizationResponse(
        focus_opportunity_matching=pref.focus_opportunity_matching,
        focus_resume_tailoring=pref.focus_resume_tailoring,
        focus_deadline_tracking=pref.focus_deadline_tracking,
        update_frequency=pref.update_frequency or "daily",
        additional_notes=pref.additional_notes,
        onboarding_step=step,
        onboarding_completed=completed,
    )


@router.put("/personalization", response_model=PersonalizationResponse)
async def update_personalization(
    body: PersonalizationUpdate,
    current_user: Annotated[UserProfile, Depends(_get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PersonalizationResponse:
    """Save the current user's AI copilot personalization preferences and advance to step 4."""
    stmt = select(UserPreference).where(UserPreference.user_id == current_user.id)
    result = await db.execute(stmt)
    pref = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if not pref:
        pref = UserPreference(
            id=uuid.uuid4(),
            user_id=current_user.id,
            focus_opportunity_matching=body.focus_opportunity_matching,
            focus_resume_tailoring=body.focus_resume_tailoring,
            focus_deadline_tracking=body.focus_deadline_tracking,
            update_frequency=body.update_frequency,
            additional_notes=body.additional_notes,
            created_at=now,
            updated_at=now,
        )
        db.add(pref)
    else:
        pref.focus_opportunity_matching = body.focus_opportunity_matching
        pref.focus_resume_tailoring = body.focus_resume_tailoring
        pref.focus_deadline_tracking = body.focus_deadline_tracking
        pref.update_frequency = body.update_frequency
        pref.additional_notes = body.additional_notes
        pref.updated_at = now

    # Advance user onboarding_step to at least 4
    user_stmt = select(User).where(User.id == current_user.id)
    user_res = await db.execute(user_stmt)
    user = user_res.scalar_one_or_none()
    if user:
        if user.onboarding_step < 4:
            user.onboarding_step = 4
        current_step = user.onboarding_step
        current_completed = user.onboarding_completed
    else:
        current_step = 4
        current_completed = False

    await db.flush()
    await db.refresh(pref)

    return PersonalizationResponse(
        focus_opportunity_matching=pref.focus_opportunity_matching,
        focus_resume_tailoring=pref.focus_resume_tailoring,
        focus_deadline_tracking=pref.focus_deadline_tracking,
        update_frequency=pref.update_frequency,
        additional_notes=pref.additional_notes,
        onboarding_step=current_step,
        onboarding_completed=current_completed,
    )

