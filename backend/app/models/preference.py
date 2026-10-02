"""UserPreference database model."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    user_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )  # e.g., "student", "professional"
    opportunity_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )  # e.g., "internship", "full_time"
    graduation_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    preferred_location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    preferred_roles: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
        default=list,
    )
    interests: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
        default=list,
    )
    # Personalization & Copilot Preferences (Step 3)
    focus_opportunity_matching: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )
    focus_resume_tailoring: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )
    focus_deadline_tracking: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )
    update_frequency: Mapped[str] = mapped_column(
        String(50),
        default="daily",
        server_default="daily",
        nullable=False,
    )  # e.g., "daily", "important_only", "weekly"
    additional_notes: Mapped[str | None] = mapped_column(
        String(300),
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
    user: Mapped[User] = relationship(
        "User",
        back_populates="preference",
    )
