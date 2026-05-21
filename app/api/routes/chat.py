"""Authenticated chat routes."""

from fastapi import APIRouter, Depends

from app.api.deps import get_chat_service, get_current_user
from app.db.models import User
from app.domain.chat import ChatRequest
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> dict:
    """Handle one authenticated chat message.

    The route only handles HTTP concerns:
    - receives the request body
    - gets the authenticated user
    - calls ChatService
    - returns the service response
    """
    return await service.handle_message(
        user_id=current_user.id,
        message=request.message,
        conversation_id=request.conversation_id,
    )