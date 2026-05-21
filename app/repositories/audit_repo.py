"""Repository for audit log database operations.

Repositories own SQL/database access only.
They should not raise HTTP exceptions or call external systems.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog


class AuditRepository:
    """Database access layer for audit log rows."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the database session used by this repository."""
        self.session = session

    async def create_audit_log(
        self,
        *,
        actor_id: int | None,
        action: str,
        target_type: str,
        target_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Insert one audit log row and return it."""
        audit_log = AuditLog(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            audit_metadata=metadata,
        )

        self.session.add(audit_log)
        await self.session.flush()
        await self.session.refresh(audit_log)

        return audit_log