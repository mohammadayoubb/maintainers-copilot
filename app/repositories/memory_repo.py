"""Repository for long-term memory database operations."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Memory


class MemoryRepository:
    """Database access layer for long-term memories."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the database session used by this repository."""
        self.session = session

    async def create_memory(
        self,
        *,
        user_id: int,
        content: str,
        memory_type: str = "semantic",
        source_conversation_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Memory:
        """Insert one long-term memory row."""
        memory = Memory(
            user_id=user_id,
            memory_type=memory_type,
            content=content,
            source_conversation_id=source_conversation_id,
            memory_metadata=metadata,
        )

        self.session.add(memory)
        await self.session.flush()
        await self.session.refresh(memory)

        return memory

    async def list_memories_for_user(self, *, user_id: int, limit: int = 50) -> list[Memory]:
        """Return recent memories for one user."""
        statement = (
            select(Memory)
            .where(Memory.user_id == user_id)
            .order_by(Memory.created_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(statement)
        return list(result.scalars().all())