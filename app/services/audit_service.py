"""Audit service.

Services own business logic and coordinate repositories.
This service records security-sensitive actions in the audit log.
"""

from typing import Any

from app.infra.redaction import redact_text
from app.repositories.audit_repo import AuditRepository


class AuditService:
    """Business logic for audit logging."""

    def __init__(self, audit_repo: AuditRepository) -> None:
        """Store the audit repository dependency."""
        self.audit_repo = audit_repo

    async def record(
        self,
        *,
        actor_id: int | None,
        action: str,
        target_type: str,
        target_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Record one audit event after redacting metadata values."""
        redacted_metadata = self._redact_metadata(metadata)

        return await self.audit_repo.create_audit_log(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata=redacted_metadata,
        )

    def _redact_metadata(self, metadata: dict[str, Any] | None) -> dict[str, Any] | None:
        """Redact string values inside audit metadata."""
        if metadata is None:
            return None

        redacted: dict[str, Any] = {}

        for key, value in metadata.items():
            if isinstance(value, str):
                redacted[key] = redact_text(value)
            else:
                redacted[key] = value

        return redacted