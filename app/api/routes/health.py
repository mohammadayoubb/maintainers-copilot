# “This file belongs in app/api/routes because it only defines an HTTP endpoint. 
# It does not connect to the database, Redis, Vault, or any external system.

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "api"}