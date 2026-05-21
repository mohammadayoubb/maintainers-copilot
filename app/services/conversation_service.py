"""Conversation service.

This service owns chat conversation business logic.
Messages are redacted before persistence.
"""

from app.domain.errors import NotFoundError
from app.infra.redaction import redact_text
from app.repositories.conversation_repo import ConversationRepository
from app.services.audit_service import AuditService


class ConversationService:
    """Business logic for conversations and messages."""

    def __init__(
        self,
        *,
        conversation_repo: ConversationRepository,
        audit_service: AuditService,
    ) -> None:
        """Store repository and service dependencies."""
        self.conversation_repo = conversation_repo
        self.audit_service = audit_service

    async def create_conversation(
        self,
        *,
        user_id: int,
        title: str | None = None,
        widget_id: str | None = None,
    ):
        """Create a new conversation for a user."""
        return await self.conversation_repo.create_conversation(
            user_id=user_id,
            title=title,
            widget_id=widget_id,
        )

    async def add_message(
        self,
        *,
        conversation_id: int,
        role: str,
        content: str,
        trace_id: str | None = None,
    ):
        """Redact and save one message."""
        redacted_content = redact_text(content)

        return await self.conversation_repo.create_message(
            conversation_id=conversation_id,
            role=role,
            content_redacted=redacted_content,
            trace_id=trace_id,
        )

    async def list_messages(self, *, conversation_id: int, limit: int = 50):
        """List messages for an existing conversation."""
        conversation = await self.conversation_repo.get_conversation_by_id(
            conversation_id=conversation_id,
        )

        if conversation is None:
            raise NotFoundError("Conversation not found.")

        return await self.conversation_repo.list_messages(
            conversation_id=conversation_id,
            limit=limit,
        )

    async def delete_conversation(
        self,
        *,
        actor_id: int,
        conversation_id: int,
    ):
        """Placeholder for later soft-delete support.

        The current repository does not yet implement soft delete.
        This method exists so the service boundary is ready for the project requirement.
        """
        conversation = await self.conversation_repo.get_conversation_by_id(
            conversation_id=conversation_id,
        )

        if conversation is None:
            raise NotFoundError("Conversation not found.")

        await self.audit_service.record(
            actor_id=actor_id,
            action="conversation_delete_requested",
            target_type="conversation",
            target_id=str(conversation_id),
            metadata={"status": "not_implemented_yet"},
        )

        return conversation