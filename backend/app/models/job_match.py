"""JobListing and DailyMatch database models for personalized job matching."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import uuid

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class JobListing(Base):
    __tablename__ = "job_listings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    external_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    source: Mapped[str] = mapped_column(
        String(100),
        default="mock",
        nullable=False,
    )
    company: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role_title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    employment_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )  # e.g., "full_time", "internship", "contract"
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    application_url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )
    deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    compensation: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    embedding_status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
    )  # "pending", "embedded", "failed"
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    fetched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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

    # Relationships
    matches: Mapped[List[DailyMatch]] = relationship(
        "DailyMatch",
        back_populates="job_listing",
        cascade="all, delete-orphan",
    )


class DailyMatch(Base):
    __tablename__ = "daily_matches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_listings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    similarity_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    preference_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    final_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    match_reasons: Mapped[list[str] | None] = mapped_column(
        JSON,
        default=list,
        nullable=True,
    )
    matched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    dismissed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    saved: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped[User] = relationship(
        "User",
        back_populates="daily_matches",
    )
    job_listing: Mapped[JobListing] = relationship(
        "JobListing",
        back_populates="matches",
    )
