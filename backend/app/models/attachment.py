from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.complaint import Complaint
    from app.models.user import User


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    complaint_id: Mapped[int] = mapped_column(
        ForeignKey("complaints.id"),
        nullable=False,
        index=True,
    )

    uploaded_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    stored_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    complaint: Mapped["Complaint"] = relationship(
        "Complaint",
        foreign_keys=[complaint_id],
        back_populates="attachments",
    )

    uploader: Mapped["User"] = relationship(
        "User",
        foreign_keys=[uploaded_by],
        back_populates="attachments",
    )
