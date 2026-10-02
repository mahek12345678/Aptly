"""Resume database model."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Resume(Base):
    __tablename__ = "resumes"

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
    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )
    file_size_bytes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    extracted_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    parsed_status: Mapped[str] = mapped_column(
        String(50),
        default="uploaded",
        nullable=False,
    )  # e.g., "uploaded", "parsing", "parsed", "failed"
    parsed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    parse_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    parsed_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped[User] = relationship(
        "User",
        back_populates="resumes",
    )

    @property
    def mime_type(self) -> str:
        from pathlib import Path
        name = self.file_name or self.file_path or ""
        ext = Path(name).suffix.lower()
        if ext == ".pdf":
            return "application/pdf"
        elif ext == ".docx":
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        return "application/octet-stream"

