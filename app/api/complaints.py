from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models.complaint import Complaint
from app.models.user import User
from app.schemas.complaint import ComplaintCreate, ComplaintResponse
from typing import List
from app.api.permissions import require_role
from app.schemas.complaint import ComplaintStatusUpdate
from fastapi import HTTPException
from app.schemas.complaint import ComplaintAssignment


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
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail="Complaint not found",
        )

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

    complaint.status = status_data.status

    db.commit()
    db.refresh(complaint)

    return complaint