"""${message}.

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# Revision identifiers used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    """Apply this migration.

    Alembic places table creation or schema changes inside this function.
    Running `alembic upgrade head` executes this function.
    """
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Revert this migration.

    Alembic places reverse operations inside this function.
    Running `alembic downgrade -1` executes this function.
    """
    ${downgrades if downgrades else "pass"}