from collections import defaultdict
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.permissions import require_role
from app.db.dependencies import get_db
from app.models.complaint import Complaint
from app.models.user import User
from app.schemas.analytics import AnalyticsResponse
from app.schemas.complaint import PaginatedComplaintResponse
from app.schemas.user import PaginatedUserResponse, UserResponse, UserStatusUpdate
from app.services.complaint_assignment import CATEGORY_TO_DEPARTMENT

ALL_CATEGORIES = ["garbage", "water", "electricity", "roads"]
ALL_DEPARTMENTS = ["sanitation", "water", "electrical", "public_works"]

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


@router.get(
    "/analytics",
    response_model=AnalyticsResponse,
)
def get_admin_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    status_counts_query = (
        db.query(Complaint.status, func.count(Complaint.id))
        .group_by(Complaint.status)
        .all()
    )
    status_counts = {status_name: count for status_name, count in status_counts_query}

    pending = status_counts.get("pending", 0)
    assigned = status_counts.get("assigned", 0)
    in_progress = status_counts.get("in_progress", 0)
    resolved = status_counts.get("resolved", 0)
    total = pending + assigned + in_progress + resolved

    category_counts_query = (
        db.query(Complaint.category, func.count(Complaint.id))
        .group_by(Complaint.category)
        .all()
    )
    by_category = {cat: 0 for cat in ALL_CATEGORIES}
    for cat, count in category_counts_query:
        by_category[cat] = count

    by_department = {dept: 0 for dept in ALL_DEPARTMENTS}
    for cat, count in by_category.items():
        dept = CATEGORY_TO_DEPARTMENT.get(cat, "other")
        by_department[dept] = by_department.get(dept, 0) + count

    resolved_complaints = (
        db.query(Complaint)
        .filter(Complaint.status == "resolved")
        .all()
    )

    dept_durations = defaultdict(list)
    all_durations = []

    for c in resolved_complaints:
        if c.created_at and c.updated_at:
            duration = (c.updated_at - c.created_at).total_seconds()
            if duration >= 0:
                all_durations.append(duration)
                dept = CATEGORY_TO_DEPARTMENT.get(c.category, "other")
                dept_durations[dept].append(duration)

    avg_resolution_time = (
        sum(all_durations) / len(all_durations) if all_durations else None
    )

    avg_by_department = {}
    for dept in ALL_DEPARTMENTS:
        durations = dept_durations.get(dept, [])
        avg_by_department[dept] = (
            sum(durations) / len(durations) if durations else 0.0
        )

    return {
        "total_complaints": total,
        "pending_complaints": pending,
        "assigned_complaints": assigned,
        "in_progress_complaints": in_progress,
        "resolved_complaints": resolved,
        "by_category": by_category,
        "by_department": by_department,
        "avg_resolution_time_seconds": avg_resolution_time,
        "avg_resolution_time_by_department": avg_by_department,
    }


@router.get(
    "/users",
    response_model=PaginatedUserResponse,
)
def get_all_users(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: Optional[str] = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    query = db.query(User)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.name.ilike(search_term),
                User.email.ilike(search_term),
            )
        )

    total = query.count()
    items = (
        query.order_by(User.id.asc())
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
    if user_id == current_user.id and not status_data.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot deactivate their own account",
        )

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_active = status_data.is_active

    db.commit()
    db.refresh(user)

    return user


@router.get(
    "/complaints",
    response_model=PaginatedComplaintResponse,
)
def get_all_complaints(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: Optional[str] = Query(default=None, max_length=20),
    category: Optional[str] = Query(default=None, max_length=50),
    priority: Optional[str] = Query(default=None, max_length=20),
    search: Optional[str] = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    query = db.query(Complaint)

    if status_filter:
        query = query.filter(Complaint.status == status_filter)

    if category:
        query = query.filter(Complaint.category == category)

    if priority:
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