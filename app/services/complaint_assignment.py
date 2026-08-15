from sqlalchemy.orm import Session

from app.models.complaint import Complaint
from app.models.user import User
from app.models.complaint_history import ComplaintStatusHistory


CATEGORY_TO_DEPARTMENT = {
    "garbage": "sanitation",
    "water": "water",
    "electricity": "electrical",
    "roads": "public_works",
}


def auto_assign_complaint(
    complaint: Complaint,
    db: Session,
    changed_by: int,
) -> User | None:

    department = CATEGORY_TO_DEPARTMENT.get(
        complaint.category
    )

    if department is None:
        return None

    authority = (
        db.query(User)
        .filter(
            User.role == "authority",
            User.department == department,
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