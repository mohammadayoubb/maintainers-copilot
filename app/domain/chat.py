"""Chat domain models.

Domain models describe the business-level shape of chat requests/responses.
They are separate from SQLAlchemy ORM models.
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request body for sending a chat message."""

    message: str = Field(min_length=1)
    conversation_id: int | None = None


class ChatResponse(BaseModel):
    """Response returned by the chat endpoint."""

    conversation_id: int
    user_message_id: int
    assistant_message_id: int
    response: str