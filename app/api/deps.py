"""FastAPI dependency helpers.

This module wires API routes to services.

Architecture rule:
- Routes call services.
- Services call repositories/infra.
- Routes should not create SQL queries directly.
"""

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.repositories.audit_repo import AuditRepository
from app.repositories.conversation_repo import ConversationRepository
from app.repositories.memory_repo import MemoryRepository
from app.repositories.widget_repo import WidgetRepository
from app.services.audit_service import AuditService
from app.services.conversation_service import ConversationService
from app.services.memory_service import MemoryService
from app.services.widget_service import WidgetService
from app.auth.users import current_active_user
from app.db.models import User
from app.domain.errors import PermissionDeniedError

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide one database session per request.

    The session is committed if the request succeeds.
    The session is rolled back if an exception happens.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_audit_service(
    session: AsyncSession = Depends(get_db_session),
) -> AuditService:
    """Create AuditService for the current request."""
    audit_repo = AuditRepository(session)
    return AuditService(audit_repo)


def get_memory_service(
    session: AsyncSession = Depends(get_db_session),
) -> MemoryService:
    """Create MemoryService for the current request."""
    audit_repo = AuditRepository(session)
    audit_service = AuditService(audit_repo)

    memory_repo = MemoryRepository(session)

    return MemoryService(
        memory_repo=memory_repo,
        audit_service=audit_service,
    )


def get_conversation_service(
    session: AsyncSession = Depends(get_db_session),
) -> ConversationService:
    """Create ConversationService for the current request."""
    audit_repo = AuditRepository(session)
    audit_service = AuditService(audit_repo)

    conversation_repo = ConversationRepository(session)

    return ConversationService(
        conversation_repo=conversation_repo,
        audit_service=audit_service,
    )


def get_widget_service(
    session: AsyncSession = Depends(get_db_session),
) -> WidgetService:
    """Create WidgetService for the current request."""
    audit_repo = AuditRepository(session)
    audit_service = AuditService(audit_repo)

    widget_repo = WidgetRepository(session)

    return WidgetService(
        widget_repo=widget_repo,
        audit_service=audit_service,
    )


async def get_current_user(
    user: User = Depends(current_active_user),
) -> User:
    """Return the current authenticated active user."""
    return user


async def get_current_admin_user(
    user: User = Depends(current_active_user),
) -> User:
    """Return the current user only if they are an admin."""
    if user.role != "admin":
        raise PermissionDeniedError("Admin access is required.")

    return user