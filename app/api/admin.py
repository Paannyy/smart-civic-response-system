from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.api.permissions import require_role
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.user import UserResponse


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