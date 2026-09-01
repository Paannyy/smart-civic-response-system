from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.attachment import Attachment
    from app.models.complaint_history import ComplaintStatusHistory
    from app.models.notification import Notification
    from app.models.user import User


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="medium",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )

    citizen_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    assigned_authority_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    citizen: Mapped["User"] = relationship(
        "User",
        foreign_keys=[citizen_id],
        back_populates="created_complaints",
    )
    assigned_authority: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[assigned_authority_id],
        back_populates="assigned_complaints",
    )
    status_history: Mapped[List["ComplaintStatusHistory"]] = relationship(
        "ComplaintStatusHistory",
        back_populates="complaint",
        cascade="all, delete-orphan",
        order_by="ComplaintStatusHistory.created_at.asc()",
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification",
        foreign_keys="Notification.complaint_id",
        back_populates="complaint",
        cascade="all, delete-orphan",
    )
    attachments: Mapped[List["Attachment"]] = relationship(
        "Attachment",
        foreign_keys="Attachment.complaint_id",
        back_populates="complaint",
        cascade="all, delete-orphan",
        order_by="Attachment.created_at.asc()",
    )