"""Repository for conversation and message database operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Conversation, Message


class ConversationRepository:
    """Database access layer for conversations and messages."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the database session used by this repository."""
        self.session = session

    async def create_conversation(
        self,
        *,
        user_id: int,
        title: str | None = None,
        widget_id: str | None = None,
    ) -> Conversation:
        """Create a new conversation for a user."""
        conversation = Conversation(
            user_id=user_id,
            title=title,
            widget_id=widget_id,
        )

        self.session.add(conversation)
        await self.session.flush()
        await self.session.refresh(conversation)

        return conversation

    async def get_conversation_by_id(self, *, conversation_id: int) -> Conversation | None:
        """Fetch one conversation by ID."""
        statement = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.deleted_at.is_(None),
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create_message(
        self,
        *,
        conversation_id: int,
        role: str,
        content_redacted: str,
        trace_id: str | None = None,
    ) -> Message:
        """Insert a message into a conversation."""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content_redacted=content_redacted,
            trace_id=trace_id,
        )

        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)

        return message

    async def list_messages(
        self,
        *,
        conversation_id: int,
        limit: int = 50,
    ) -> list[Message]:
        """Return recent messages for a conversation."""
        statement = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )

        result = await self.session.execute(statement)
        return list(result.scalars().all())