from typing import Optional
from sqlalchemy.orm import Session

from app.models.complaint import Complaint
from app.models.notification import Notification
from app.models.user import User
from app.services.email_service import email_service


def create_notification(
    db: Session,
    user_id: int,
    type: str,
    title: str,
    message: str,
    complaint_id: Optional[int] = None,
) -> Notification:
    # Deduplicate: check if an identical unread notification was created recently
    existing = (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.complaint_id == complaint_id,
            Notification.type == type,
            Notification.title == title,
            Notification.message == message,
            Notification.is_read.is_(False),
        )
        .first()
    )
    if existing:
        return existing

    notification = Notification(
        user_id=user_id,
        complaint_id=complaint_id,
        type=type,
        title=title,
        message=message,
    )
    db.add(notification)

    # Optional email notification (non-blocking, fails gracefully)
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.email:
            email_service.send_complaint_notification(
                to_email=user.email,
                title=title,
                message=message,
            )
    except Exception:
        pass

    return notification


def notify_complaint_created(db: Session, complaint: Complaint) -> None:
    create_notification(
        db=db,
        user_id=complaint.citizen_id,
        type="complaint_created",
        title="Complaint Submitted",
        message=f"Your complaint '{complaint.title}' (#{complaint.id}) has been recorded.",
        complaint_id=complaint.id,
    )


def notify_complaint_assigned(
    db: Session,
    complaint: Complaint,
    authority_id: int,
) -> None:
    # Notify the assigned officer
    create_notification(
        db=db,
        user_id=authority_id,
        type="complaint_assigned",
        title="New Complaint Assigned",
        message=f"Complaint #{complaint.id} ('{complaint.title}') has been assigned to you.",
        complaint_id=complaint.id,
    )

    # Notify the citizen
    create_notification(
        db=db,
        user_id=complaint.citizen_id,
        type="complaint_assigned",
        title="Complaint Assigned",
        message=f"Your complaint #{complaint.id} has been assigned to an officer.",
        complaint_id=complaint.id,
    )


def notify_complaint_status_changed(
    db: Session,
    complaint: Complaint,
    new_status: str,
    changed_by: int,
) -> None:
    status_display = new_status.replace("_", " ").title()

    if new_status == "resolved":
        create_notification(
            db=db,
            user_id=complaint.citizen_id,
            type="complaint_resolved",
            title="Complaint Resolved",
            message=f"Your complaint #{complaint.id} ('{complaint.title}') has been resolved.",
            complaint_id=complaint.id,
        )
    else:
        create_notification(
            db=db,
            user_id=complaint.citizen_id,
            type="status_updated",
            title=f"Status Updated: {status_display}",
            message=f"Your complaint #{complaint.id} status is now '{status_display}'.",
            complaint_id=complaint.id,
        )
