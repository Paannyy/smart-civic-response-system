from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.permissions import require_role
from app.db.dependencies import get_db
from app.models.complaint import Complaint
from app.models.complaint_history import ComplaintStatusHistory
from app.models.user import User
from app.schemas.complaint import (
    ComplaintAssignment,
    ComplaintCreate,
    ComplaintHistoryResponse,
    ComplaintResponse,
    ComplaintStatusUpdate,
    PaginatedComplaintResponse,
)
from app.services.complaint_assignment import (
    CATEGORY_TO_DEPARTMENT,
    auto_assign_complaint,
)
from app.services.notification_service import (
    notify_complaint_assigned,
    notify_complaint_created,
    notify_complaint_status_changed,
)

ALLOWED_STATUS_TRANSITIONS = {
    "pending": {"assigned"},
    "assigned": {"in_progress"},
    "in_progress": {"resolved"},
    "resolved": set(),
}

router = APIRouter(
    prefix="/complaints",
    tags=["Complaints"],
)


@router.post(
    "/",
    response_model=ComplaintResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_complaint(
    complaint_data: ComplaintCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    complaint = Complaint(
        title=complaint_data.title,
        description=complaint_data.description,
        category=complaint_data.category,
        priority=complaint_data.priority,
        status="pending",
        citizen_id=current_user.id,
    )

    db.add(complaint)
    db.flush()

    notify_complaint_created(db=db, complaint=complaint)

    assigned_authority = auto_assign_complaint(
        complaint=complaint,
        db=db,
        changed_by=current_user.id,
    )

    if assigned_authority:
        notify_complaint_assigned(
            db=db,
            complaint=complaint,
            authority_id=assigned_authority.id,
        )

    db.commit()
    db.refresh(complaint)

    return complaint


@router.get(
    "/",
    response_model=PaginatedComplaintResponse,
)
def get_my_complaints(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, max_length=20),
    category: str | None = Query(default=None, max_length=50),
    priority: str | None = Query(default=None, max_length=20),
    search: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Complaint).filter(
        Complaint.citizen_id == current_user.id
    )

    if status_filter is not None:
        query = query.filter(Complaint.status == status_filter)

    if category is not None:
        query = query.filter(Complaint.category == category)

    if priority is not None:
        query = query.filter(Complaint.priority == priority)

    if search:
        search_term = f"%{search.strip()}%"
        search_clauses = [
            Complaint.title.ilike(search_term),
            Complaint.description.ilike(search_term),
        ]
        if search.strip().isdigit():
            search_clauses.append(Complaint.id == int(search.strip()))
        query = query.filter(or_(*search_clauses))

    total = query.count()
    items = (
        query.order_by(Complaint.created_at.desc(), Complaint.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/assigned",
    response_model=PaginatedComplaintResponse,
)
def get_assigned_complaints(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, max_length=20),
    category: str | None = Query(default=None, max_length=50),
    priority: str | None = Query(default=None, max_length=20),
    search: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("authority", "admin")
    ),
):
    query = db.query(Complaint).filter(
        Complaint.assigned_authority_id == current_user.id
    )

    if status_filter is not None:
        query = query.filter(Complaint.status == status_filter)

    if category is not None:
        query = query.filter(Complaint.category == category)

    if priority is not None:
        query = query.filter(Complaint.priority == priority)

    if search:
        search_term = f"%{search.strip()}%"
        search_clauses = [
            Complaint.title.ilike(search_term),
            Complaint.description.ilike(search_term),
        ]
        if search.strip().isdigit():
            search_clauses.append(Complaint.id == int(search.strip()))
        query = query.filter(or_(*search_clauses))

    total = query.count()
    items = (
        query.order_by(Complaint.created_at.desc(), Complaint.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/{complaint_id}/history",
    response_model=List[ComplaintHistoryResponse],
)
def get_complaint_history(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    complaint = (
        db.query(Complaint)
        .filter(Complaint.id == complaint_id)
        .first()
    )

    if complaint is None:
        raise HTTPException(
            status_code=404,
            detail="Complaint not found",
        )

    if current_user.role == "admin":
        allowed = True
    elif current_user.role == "authority":
        allowed = complaint.assigned_authority_id == current_user.id
    else:
        allowed = complaint.citizen_id == current_user.id

    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to view this complaint history",
        )

    history = (
        db.query(ComplaintStatusHistory)
        .filter(
            ComplaintStatusHistory.complaint_id == complaint_id
        )
        .order_by(ComplaintStatusHistory.created_at.asc())
        .all()
    )

    return history


@router.get(
    "/{complaint_id}",
    response_model=ComplaintResponse,
)
def get_complaint_by_id(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    complaint = (
        db.query(Complaint)
        .filter(Complaint.id == complaint_id)
        .first()
    )

    if complaint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found",
        )

    if current_user.role == "admin":
        allowed = True
    elif current_user.role == "authority":
        allowed = complaint.assigned_authority_id == current_user.id
    else:
        allowed = complaint.citizen_id == current_user.id

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to view this complaint",
        )

    return complaint


@router.patch(
    "/{complaint_id}/assign",
    response_model=ComplaintResponse,
)
def assign_complaint(
    complaint_id: int,
    assignment_data: ComplaintAssignment,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    complaint = (
        db.query(Complaint)
        .filter(Complaint.id == complaint_id)
        .first()
    )

    if complaint is None:
        raise HTTPException(
            status_code=404,
            detail="Complaint not found",
        )

    authority = (
        db.query(User)
        .filter(
            User.id == assignment_data.authority_id,
            User.role == "authority",
            User.is_active.is_(True),
        )
        .first()
    )

    if authority is None:
        raise HTTPException(
            status_code=404,
            detail="Authority not found",
        )

    expected_department = CATEGORY_TO_DEPARTMENT.get(complaint.category)

    if (
        expected_department is not None
        and authority.department != expected_department
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Authority department does not match "
                f"complaint category: {complaint.category}"
            ),
        )

    complaint.assigned_authority_id = authority.id
    complaint.status = "assigned"

    history = ComplaintStatusHistory(
        complaint_id=complaint.id,
        status="assigned",
        changed_by=current_user.id,
    )

    db.add(history)

    notify_complaint_assigned(
        db=db,
        complaint=complaint,
        authority_id=authority.id,
    )

    db.commit()
    db.refresh(complaint)

    return complaint


@router.patch(
    "/{complaint_id}/status",
    response_model=ComplaintResponse,
)
def update_complaint_status(
    complaint_id: int,
    status_data: ComplaintStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("authority", "admin")
    ),
):
    complaint = (
        db.query(Complaint)
        .filter(Complaint.id == complaint_id)
        .first()
    )

    if complaint is None:
        raise HTTPException(
            status_code=404,
            detail="Complaint not found",
        )

    if (
        current_user.role == "authority"
        and complaint.assigned_authority_id != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="Complaint is not assigned to you",
        )

    allowed_next_statuses = ALLOWED_STATUS_TRANSITIONS.get(
        complaint.status,
        set(),
    )

    if status_data.status not in allowed_next_statuses:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid status transition: "
                f"{complaint.status} -> {status_data.status}"
            ),
        )

    complaint.status = status_data.status

    history = ComplaintStatusHistory(
        complaint_id=complaint.id,
        status=status_data.status,
        changed_by=current_user.id,
    )

    db.add(history)

    notify_complaint_status_changed(
        db=db,
        complaint=complaint,
        new_status=status_data.status,
        changed_by=current_user.id,
    )

    db.commit()
    db.refresh(complaint)

    return complaint