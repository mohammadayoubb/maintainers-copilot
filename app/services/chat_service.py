"""Chat service.

This service owns the authenticated chatbot flow.

Current Batch 10 behavior:
- create or reuse a conversation
- persist the user message
- generate a simple placeholder assistant response
- persist the assistant message

Later batches will replace the placeholder response with a tool-calling LLM.
"""

from app.domain.chat import ChatRequest, ChatResponse
from app.domain.errors import NotFoundError
from app.repositories.conversation_repo import ConversationRepository
from app.services.conversation_service import ConversationService


class ChatService:
    """Business logic for authenticated chat."""

    def __init__(
        self,
        *,
        conversation_repo: ConversationRepository,
        conversation_service: ConversationService,
    ) -> None:
        """Store service/repository dependencies."""
        self.conversation_repo = conversation_repo
        self.conversation_service = conversation_service

    async def handle_message(
        self,
        *,
        user_id: int,
        request: ChatRequest,
    ) -> ChatResponse:
        """Handle one authenticated chat message."""
        conversation_id = request.conversation_id

        if conversation_id is None:
            conversation = await self.conversation_service.create_conversation(
                user_id=user_id,
                title=self._build_title(request.message),
            )
            conversation_id = conversation.id
        else:
            conversation = await self.conversation_repo.get_conversation_by_id(
                conversation_id=conversation_id,
            )

            if conversation is None:
                raise NotFoundError("Conversation not found.")

            if conversation.user_id != user_id:
                raise NotFoundError("Conversation not found.")

        user_message = await self.conversation_service.add_message(
            conversation_id=conversation_id,
            role="user",
            content=request.message,
        )

        assistant_text = self._build_placeholder_response(request.message)

        assistant_message = await self.conversation_service.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_text,
        )

        return ChatResponse(
            conversation_id=conversation_id,
            user_message_id=user_message.id,
            assistant_message_id=assistant_message.id,
            response=assistant_text,
        )

    def _build_title(self, message: str) -> str:
        """Create a short conversation title from the first message."""
        normalized = " ".join(message.split())

        if len(normalized) <= 60:
            return normalized

        return normalized[:57] + "..."

    def _build_placeholder_response(self, message: str) -> str:
        """Return a simple placeholder assistant response.

        This proves the chat persistence/auth flow before adding the LLM.
        """
        return (
            "Chat foundation is working. "
            "I received your message and saved it to the conversation. "
            f"Message preview: {message[:120]}"
        )