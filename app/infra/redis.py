"""Redis infrastructure helpers.

Redis is used for short-term conversation memory and cache-like state.
Long-term memory stays in Postgres.
"""

from __future__ import annotations

from redis.asyncio import Redis


DEFAULT_REDIS_URL = "redis://redis:6379/0"


def get_redis_client() -> Redis:
    """Create an async Redis client.

    The Docker Compose service name is `redis`, so the API container can reach it
    at redis://redis:6379/0.
    """
    return Redis.from_url(
        DEFAULT_REDIS_URL,
        decode_responses=True,
    )