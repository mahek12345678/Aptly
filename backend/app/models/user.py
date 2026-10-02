"""User database model."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.preference import UserPreference
    from app.models.resume import Resume
    from app.models.application import JobApplication
    from app.models.job_match import DailyMatch


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    google_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    profile_picture_url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    onboarding_completed: Mapped[bool] = mapped_column(
        default=False,
        server_default="false",
        nullable=False,
    )
    onboarding_step: Mapped[int] = mapped_column(
        default=1,
        server_default="1",
        nullable=False,
    )

    # Relationships
    preference: Mapped[Optional[UserPreference]] = relationship(
        "UserPreference",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    resumes: Mapped[list[Resume]] = relationship(
        "Resume",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    applications: Mapped[list[JobApplication]] = relationship(
        "JobApplication",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    daily_matches: Mapped[list[DailyMatch]] = relationship(
        "DailyMatch",
        back_populates="user",
        cascade="all, delete-orphan",
    )
