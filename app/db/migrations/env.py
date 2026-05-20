"""Alembic migration environment.

This file connects Alembic to the application's SQLAlchemy models.

Alembic uses this file when running commands like:
- alembic current
- alembic revision --autogenerate
- alembic upgrade head

Important:
Alembic needs access to Base.metadata so it can discover ORM tables
defined in app/db/models.py.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.db.models import Base
import os
# Alembic configuration object.
# This reads values from alembic.ini.
config = context.config

# Configure Python logging using the logging section in alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# Allow Docker Compose to override the database URL.
# From the laptop, alembic.ini uses localhost.
# From Docker, docker-compose.yml passes db as the hostname.
database_sync_url = os.getenv("DATABASE_SYNC_URL")

if database_sync_url:
    config.set_main_option("sqlalchemy.url", database_sync_url)


# This is the metadata Alembic uses for autogeneration.
# When we run alembic revision --autogenerate, Alembic compares:
# - this metadata
# - the actual database schema
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without creating a live database connection.

    Offline mode generates SQL scripts instead of applying changes directly.
    We usually will not use this during normal local development, but Alembic
    expects the function to exist.
    """
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a live database connection.

    This is the normal mode we use locally.
    Alembic connects to Postgres, checks the current schema version,
    and applies migration files.
    """
    configuration = config.get_section(config.config_ini_section)

    if configuration is None:
        raise RuntimeError("Alembic configuration section is missing.")

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# Alembic decides which mode to run in.
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()