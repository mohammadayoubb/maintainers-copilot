"""Authentication schemas.

These schemas define what the API returns for auth-related user data.
"""

from fastapi_users import schemas


class UserRead(schemas.BaseUser[int]):
    """User data returned by auth endpoints."""

    role: str


class UserCreate(schemas.BaseUserCreate):
    """User registration input."""

    role: str = "user"


class UserUpdate(schemas.BaseUserUpdate):
    """User update input."""

    role: str | None = None