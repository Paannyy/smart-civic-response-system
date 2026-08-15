from sqlalchemy.orm import Session

from app.models.complaint import Complaint
from app.models.user import User
from app.models.complaint_history import ComplaintStatusHistory


SUPPORTED_CATEGORIES = {
    "garbage",
    "electricity",
    "water",
    "roads",
}


def auto_assign_complaint(
    complaint: Complaint,
    db: Session,
    changed_by: int,
) -> User | None:

    if complaint.category not in SUPPORTED_CATEGORIES:
        return None

    authority = (
        db.query(User)
        .filter(
            User.role == "authority",
            User.is_active.is_(True),
        )
        .order_by(User.id.asc())
        .first()
    )

    if authority is None:
        return None

    complaint.assigned_authority_id = authority.id
    complaint.status = "assigned"

    history = ComplaintStatusHistory(
        complaint_id=complaint.id,
        status="assigned",
        changed_by=changed_by,
    )

    db.add(history)

    return authority