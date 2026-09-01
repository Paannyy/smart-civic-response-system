from datetime import datetime, timezone
from typing import List, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.attachment import Attachment
    from app.models.complaint import Complaint
    from app.models.complaint_history import ComplaintStatusHistory
    from app.models.notification import Notification


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="citizen",
    )
    department: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
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

    created_complaints: Mapped[List["Complaint"]] = relationship(
        "Complaint",
        foreign_keys="Complaint.citizen_id",
        back_populates="citizen",
        cascade="all, delete-orphan",
    )
    assigned_complaints: Mapped[List["Complaint"]] = relationship(
        "Complaint",
        foreign_keys="Complaint.assigned_authority_id",
        back_populates="assigned_authority",
    )
    status_changes: Mapped[List["ComplaintStatusHistory"]] = relationship(
        "ComplaintStatusHistory",
        foreign_keys="ComplaintStatusHistory.changed_by",
        back_populates="changed_by_user",
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification",
        foreign_keys="Notification.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    attachments: Mapped[List["Attachment"]] = relationship(
        "Attachment",
        foreign_keys="Attachment.uploaded_by",
        back_populates="uploader",
        cascade="all, delete-orphan",
    )