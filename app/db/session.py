"""Database session configuration.

This file owns the SQLAlchemy database connection setup.

Important architecture rule:
Database connection setup belongs in app/db.
Routes should not create database engines directly.
Repositories receive database sessions and run SQL queries.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings


def build_database_url() -> str:
    """Build the async PostgreSQL database URL.

    The API uses DATABASE_URL when it is provided.

    Inside Docker Compose, DATABASE_URL should use the db service hostname:
    postgresql+asyncpg://maintainer:maintainer@db:5432/maintainers_copilot

    Outside Docker, local scripts can fall back to localhost.
    """
    settings = get_settings()

    if settings.database_url:
        return settings.database_url

    return (
        "postgresql+asyncpg://"
        "maintainer:maintainer"
        f"@localhost:{settings.postgres_port}"
        "/maintainers_copilot"
    )


engine = create_async_engine(
    build_database_url(),
    echo=False,
)


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide one database session for a request."""
    async with AsyncSessionLocal() as session:
        yield session