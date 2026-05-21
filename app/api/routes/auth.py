"""Authentication routes.

This module exposes a small authenticated profile endpoint.
The built-in register/login routes are included in app/main.py.
"""

from typing import Any

from fastapi import APIRouter, Depends

from app.auth.users import current_active_user
from app.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
async def get_me(user: User = Depends(current_active_user)) -> dict[str, Any]:
    """Return the currently authenticated user."""
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "is_superuser": user.is_superuser,
    }