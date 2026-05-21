"""Short-term conversation memory service.

This service stores recent chat messages in Redis with an explicit TTL.

The goal is not permanent memory. It is temporary conversation context.
Permanent memory is handled by MemoryService and stored in Postgres.
"""

from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis

from app.infra.redaction import redact_text


SHORT_TERM_MEMORY_TTL_SECONDS = 60 * 30


class ShortTermMemoryService:
    """Store and retrieve recent conversation messages from Redis."""

    def __init__(
        self,
        redis_client: Redis,
        ttl_seconds: int = SHORT_TERM_MEMORY_TTL_SECONDS,
    ) -> None:
        """Store Redis client and TTL configuration."""
        self.redis_client = redis_client
        self.ttl_seconds = ttl_seconds

    async def append_message(
        self,
        *,
        conversation_id: int,
        role: str,
        content: str,
    ) -> None:
        """Append one redacted message to short-term memory.

        The Redis key expires after ttl_seconds. Every append refreshes the TTL,
        which keeps active conversations alive and lets inactive ones expire.
        """
        key = self._conversation_key(conversation_id)

        payload = {
            "role": role,
            "content": redact_text(content),
        }

        await self.redis_client.rpush(key, json.dumps(payload))
        await self.redis_client.expire(key, self.ttl_seconds)

    async def get_recent_messages(
        self,
        *,
        conversation_id: int,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Return the most recent short-term messages for a conversation."""
        key = self._conversation_key(conversation_id)

        raw_messages = await self.redis_client.lrange(key, -limit, -1)

        messages: list[dict[str, Any]] = []

        for raw_message in raw_messages:
            messages.append(json.loads(raw_message))

        return messages

    async def clear_conversation(
        self,
        *,
        conversation_id: int,
    ) -> None:
        """Delete short-term memory for one conversation."""
        key = self._conversation_key(conversation_id)
        await self.redis_client.delete(key)

    def _conversation_key(self, conversation_id: int) -> str:
        """Build the Redis key for one conversation."""
        return f"chat:conversation:{conversation_id}:messages"