"""Memory service.

This service owns long-term memory business logic.
Memory writes must be explicit and audited.
"""

from typing import Any

from app.infra.redaction import redact_text
from app.repositories.memory_repo import MemoryRepository
from app.services.audit_service import AuditService


class MemoryService:
    """Business logic for long-term chatbot memory."""

    def __init__(
        self,
        *,
        memory_repo: MemoryRepository,
        audit_service: AuditService,
    ) -> None:
        """Store repository and service dependencies."""
        self.memory_repo = memory_repo
        self.audit_service = audit_service

    async def write_memory(
        self,
        *,
        user_id: int,
        content: str,
        memory_type: str = "semantic",
        source_conversation_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Write explicit long-term memory and create an audit log row."""
        redacted_content = redact_text(content)

        memory = await self.memory_repo.create_memory(
            user_id=user_id,
            content=redacted_content,
            memory_type=memory_type,
            source_conversation_id=source_conversation_id,
            metadata=metadata,
        )

        await self.audit_service.record(
            actor_id=user_id,
            action="memory_write",
            target_type="memory",
            target_id=str(memory.id),
            metadata={
                "memory_type": memory_type,
                "source_conversation_id": source_conversation_id,
                "content_preview": redacted_content[:120],
            },
        )

        return memory

    async def list_user_memories(self, *, user_id: int, limit: int = 50):
        """List recent long-term memories for one user."""
        return await self.memory_repo.list_memories_for_user(
            user_id=user_id,
            limit=limit,
        )