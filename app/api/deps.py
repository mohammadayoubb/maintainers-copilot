"""FastAPI dependency helpers.

This file contains reusable dependencies for API routes.

Important architecture rule:
Routes should receive dependencies from this file instead of creating
database sessions, clients, or services directly.

For now, this file exposes the database session dependency.
Later, it can also expose:
- current authenticated user
- service objects
- admin-only access checks
- request ID / trace ID helpers
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session to FastAPI routes.

    This wraps the lower-level app.db.session.get_db_session function.

    Why wrap it here?
    Because API routes should import dependencies from app/api/deps.py,
    not directly from lower-level infrastructure or database modules.
    """
    async for session in get_db_session():
        yield session