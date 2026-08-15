from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api.permissions import require_role
from app.db.dependencies import get_db
from app.models.user import User
from app.models.complaint import Complaint
from app.schemas.user import UserResponse, UserStatusUpdate
from app.schemas.complaint import ComplaintResponse


router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


@router.get(
    "/users",
    response_model=List[UserResponse],
)
def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    users = (
        db.query(User)
        .order_by(User.id.asc())
        .all()
    )

    return users


@router.patch(
    "/users/{user_id}/status",
    response_model=UserResponse,
)
def update_user_status(
    user_id: int,
    status_data: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    user.is_active = status_data.is_active

    db.commit()
    db.refresh(user)

    return user


@router.get(
    "/complaints",
    response_model=List[ComplaintResponse],
)
def get_all_complaints(
    status_filter: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    query = db.query(Complaint)

    if status_filter:
        query = query.filter(
            Complaint.status == status_filter
        )

    if category:
        query = query.filter(
            Complaint.category == category
        )

    if priority:
        query = query.filter(
            Complaint.priority == priority
        )

    complaints = (
        query
        .order_by(Complaint.id.asc())
        .all()
    )

    return complaints