from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.api.dependencies import get_current_user
from app.api.permissions import require_role
from app.db.dependencies import get_db

from app.models.complaint import Complaint
from app.models.user import User
from app.models.complaint_history import ComplaintStatusHistory

from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintResponse,
    ComplaintStatusUpdate,
    ComplaintAssignment,
    ComplaintHistoryResponse,
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
    db.commit()
    db.refresh(complaint)

    return complaint


@router.get(
    "/",
    response_model=List[ComplaintResponse],
)
def get_my_complaints(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    complaints = (
        db.query(Complaint)
        .filter(Complaint.citizen_id == current_user.id)
        .all()
    )

    return complaints


@router.get(
    "/assigned",
    response_model=List[ComplaintResponse],
)
def get_assigned_complaints(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("authority", "admin")
    ),
):
    complaints = (
        db.query(Complaint)
        .filter(
            Complaint.assigned_authority_id == current_user.id
        )
        .all()
    )

    return complaints


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
def get_my_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    complaint = (
        db.query(Complaint)
        .filter(
            Complaint.id == complaint_id,
            Complaint.citizen_id == current_user.id,
        )
        .first()
    )

    if complaint is None:
        raise HTTPException(
            status_code=404,
            detail="Complaint not found",
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

    complaint.assigned_authority_id = authority.id
    complaint.status = "assigned"

    history = ComplaintStatusHistory(
        complaint_id=complaint.id,
        status="assigned",
        changed_by=current_user.id,
    )

    db.add(history)

    db.commit()
    db.refresh(complaint)


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

    db.commit()
    db.refresh(complaint)

    return complaint