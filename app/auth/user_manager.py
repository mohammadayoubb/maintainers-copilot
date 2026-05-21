"""User manager for fastapi-users.

This module connects fastapi-users to our SQLAlchemy user table.
"""

from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, IntegerIDMixin
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.session import get_db_session


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    """User manager hooks for registration and auth events."""

    reset_password_token_secret = "temporary-reset-secret"
    verification_token_secret = "temporary-verification-secret"

    async def on_after_register(
        self,
        user: User,
        request: Request | None = None,
    ) -> None:
        """Run after a user registers."""
        # Keep this side-effect light for now.
        # Later we can audit registration events if needed.
        return None


async def get_user_db(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncGenerator[SQLAlchemyUserDatabase[User, int], None]:
    """Provide fastapi-users database adapter."""
    yield SQLAlchemyUserDatabase(session, User)


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase[User, int] = Depends(get_user_db),
) -> AsyncGenerator[UserManager, None]:
    """Provide the user manager dependency."""
    yield UserManager(user_db)