"""Authenticated chat routes."""

from fastapi import APIRouter, Depends

from app.api.deps import get_chat_service, get_current_user
from app.db.models import User
from app.domain.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """Send one authenticated chat message."""
    return await service.handle_message(
        user_id=current_user.id,
        request=request,
    )