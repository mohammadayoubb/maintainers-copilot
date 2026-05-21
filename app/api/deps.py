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

from app.auth.users import current_active_user
from app.db.models import User
from app.db.session import AsyncSessionLocal
from app.domain.errors import PermissionDeniedError
import app.infra.model_client as model_client
from app.infra.redis import get_redis_client
from app.repositories.audit_repo import AuditRepository
from app.repositories.conversation_repo import ConversationRepository
from app.repositories.memory_repo import MemoryRepository
from app.repositories.widget_repo import WidgetRepository
from app.services.audit_service import AuditService
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService
from app.services.memory_service import MemoryService
from app.services.rag_service import RagService
from app.services.short_term_memory_service import ShortTermMemoryService
from app.services.widget_service import WidgetService


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


def get_audit_repository(
    session: AsyncSession = Depends(get_db_session),
) -> AuditRepository:
    """Create AuditRepository for the current request."""
    return AuditRepository(session)


def get_memory_repository(
    session: AsyncSession = Depends(get_db_session),
) -> MemoryRepository:
    """Create MemoryRepository for the current request."""
    return MemoryRepository(session)


def get_conversation_repository(
    session: AsyncSession = Depends(get_db_session),
) -> ConversationRepository:
    """Create ConversationRepository for the current request."""
    return ConversationRepository(session)


def get_widget_repository(
    session: AsyncSession = Depends(get_db_session),
) -> WidgetRepository:
    """Create WidgetRepository for the current request."""
    return WidgetRepository(session)


def get_audit_service(
    audit_repo: AuditRepository = Depends(get_audit_repository),
) -> AuditService:
    """Create AuditService for the current request."""
    return AuditService(audit_repo)


def get_memory_service(
    memory_repo: MemoryRepository = Depends(get_memory_repository),
    audit_service: AuditService = Depends(get_audit_service),
) -> MemoryService:
    """Create MemoryService for the current request."""
    return MemoryService(
        memory_repo=memory_repo,
        audit_service=audit_service,
    )


def get_conversation_service(
    conversation_repo: ConversationRepository = Depends(get_conversation_repository),
    audit_service: AuditService = Depends(get_audit_service),
) -> ConversationService:
    """Create ConversationService for the current request."""
    return ConversationService(
        conversation_repo=conversation_repo,
        audit_service=audit_service,
    )


def get_widget_service(
    widget_repo: WidgetRepository = Depends(get_widget_repository),
    audit_service: AuditService = Depends(get_audit_service),
) -> WidgetService:
    """Create WidgetService for the current request."""
    return WidgetService(
        widget_repo=widget_repo,
        audit_service=audit_service,
    )


def get_rag_service() -> RagService:
    """Create RagService for the current request."""
    return RagService()


def get_short_term_memory_service() -> ShortTermMemoryService:
    """Create ShortTermMemoryService for the current request."""
    return ShortTermMemoryService(redis_client=get_redis_client())


def get_chat_service(
    conversation_repo: ConversationRepository = Depends(get_conversation_repository),
    memory_service: MemoryService = Depends(get_memory_service),
    rag_service: RagService = Depends(get_rag_service),
    short_term_memory_service: ShortTermMemoryService = Depends(
        get_short_term_memory_service
    ),
) -> ChatService:
    """Create ChatService with chatbot tool dependencies."""
    return ChatService(
        conversation_repo=conversation_repo,
        memory_service=memory_service,
        rag_service=rag_service,
        model_client=model_client,
        short_term_memory_service=short_term_memory_service,
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