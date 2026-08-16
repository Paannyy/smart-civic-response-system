from fastapi import Depends, HTTPException, status

from app.api.dependencies import get_current_user
from app.models.user import User


def require_role(*required_roles: str):
    def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:

        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return current_user

    return role_checker