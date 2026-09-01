from sqlalchemy import func
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

ACTIVE_WORKLOAD_STATUSES = ("assigned", "in_progress")


def auto_assign_complaint(
    complaint: Complaint,
    db: Session,
    changed_by: int,
) -> User | None:
    department = CATEGORY_TO_DEPARTMENT.get(complaint.category)

    if department is None:
        return None

    workload_count = func.count(Complaint.id).label("workload")

    authority = (
        db.query(User)
        .outerjoin(
            Complaint,
            (Complaint.assigned_authority_id == User.id)
            & (Complaint.status.in_(ACTIVE_WORKLOAD_STATUSES)),
        )
        .filter(
            User.role == "authority",
            User.department == department,
            User.is_active.is_(True),
        )
        .group_by(User.id)
        .order_by(workload_count.asc(), User.id.asc())
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