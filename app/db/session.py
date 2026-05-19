"""Database session configuration.

This file owns the SQLAlchemy database connection setup.

Important architecture rule:
Database connection setup belongs in app/db.
Routes should not create database engines directly.
Repositories will later receive database sessions and run SQL queries.

For now, we define the async engine and session factory.
Later, Alembic migrations and repositories will use this database setup.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings


def build_database_url() -> str:
    """Build the async PostgreSQL database URL.

    In the final project, the database password should come from Vault.
    For the foundation stage, we use the local Docker Compose credentials.

    Docker Compose database values:
    - user: maintainer
    - password: maintainer
    - database: maintainers_copilot
    - host: db inside Docker, localhost outside Docker

    We use localhost here for local script/testing access.
    Inside Docker, this can later be changed to use the db service hostname.
    """
    settings = get_settings()

    return (
        "postgresql+asyncpg://"
        "maintainer:maintainer"
        f"@localhost:{settings.postgres_port}"
        "/maintainers_copilot"
    )


# SQLAlchemy async engine.
# The engine manages database connections.
engine = create_async_engine(
    build_database_url(),
    echo=False,
)


# Session factory.
# Repositories will use sessions created from this factory to query the database.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide one database session for a request.

    FastAPI dependencies can use this function later.

    The session is opened before the route/service runs and automatically
    closed after the request finishes.
    """
    async with AsyncSessionLocal() as session:
        yield session