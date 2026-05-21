"""Temporary Day 4 development routes.

These routes are only used to test the Day 4 service/repository/database flow
before real authentication and production routes are added.

Architecture rule:
Routes only handle HTTP input/output and call services.
They do not talk to SQLAlchemy directly.
"""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import (
    get_conversation_service,
    get_memory_service,
    get_widget_service,
)
from app.services.conversation_service import ConversationService
from app.services.memory_service import MemoryService
from app.services.widget_service import WidgetService

router = APIRouter(prefix="/dev/day4", tags=["day4-dev"])


class CreateConversationRequest(BaseModel):
    """Request body for creating a test conversation."""

    user_id: int
    title: str | None = None
    widget_id: str | None = None


class AddMessageRequest(BaseModel):
    """Request body for adding a test message."""

    role: str = Field(pattern="^(user|assistant|tool|system)$")
    content: str
    trace_id: str | None = None


class WriteMemoryRequest(BaseModel):
    """Request body for writing test long-term memory."""

    user_id: int
    content: str
    memory_type: str = "semantic"
    source_conversation_id: int | None = None
    metadata: dict[str, Any] | None = None


class CreateWidgetRequest(BaseModel):
    """Request body for creating a test widget config."""

    actor_id: int | None = None
    allowed_origins: list[str]
    theme: dict[str, Any] = Field(
        default_factory=lambda: {
            "primary_color": "#2563eb",
            "position": "bottom-right",
        }
    )
    greeting: str = "How can I help?"
    enabled_tools: list[str] = Field(
        default_factory=lambda: [
            "classify_issue",
            "extract_entities",
            "summarize_thread",
            "rag_answer",
        ]
    )


@router.post("/conversations")
async def create_conversation(
    request: CreateConversationRequest,
    service: ConversationService = Depends(get_conversation_service),
) -> dict[str, Any]:
    """Create a test conversation."""
    conversation = await service.create_conversation(
        user_id=request.user_id,
        title=request.title,
        widget_id=request.widget_id,
    )

    return {
        "id": conversation.id,
        "user_id": conversation.user_id,
        "title": conversation.title,
        "widget_id": conversation.widget_id,
        "created_at": conversation.created_at,
    }


@router.post("/conversations/{conversation_id}/messages")
async def add_message(
    conversation_id: int,
    request: AddMessageRequest,
    service: ConversationService = Depends(get_conversation_service),
) -> dict[str, Any]:
    """Add a redacted message to a test conversation."""
    message = await service.add_message(
        conversation_id=conversation_id,
        role=request.role,
        content=request.content,
        trace_id=request.trace_id,
    )

    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "role": message.role,
        "content_redacted": message.content_redacted,
        "trace_id": message.trace_id,
        "created_at": message.created_at,
    }


@router.get("/conversations/{conversation_id}/messages")
async def list_messages(
    conversation_id: int,
    service: ConversationService = Depends(get_conversation_service),
) -> dict[str, Any]:
    """List messages for a test conversation."""
    messages = await service.list_messages(conversation_id=conversation_id)

    return {
        "conversation_id": conversation_id,
        "messages": [
            {
                "id": message.id,
                "role": message.role,
                "content_redacted": message.content_redacted,
                "trace_id": message.trace_id,
                "created_at": message.created_at,
            }
            for message in messages
        ],
    }


@router.post("/memories")
async def write_memory(
    request: WriteMemoryRequest,
    service: MemoryService = Depends(get_memory_service),
) -> dict[str, Any]:
    """Write explicit test memory."""
    memory = await service.write_memory(
        user_id=request.user_id,
        content=request.content,
        memory_type=request.memory_type,
        source_conversation_id=request.source_conversation_id,
        metadata=request.metadata,
    )

    return {
        "id": memory.id,
        "user_id": memory.user_id,
        "memory_type": memory.memory_type,
        "content": memory.content,
        "source_conversation_id": memory.source_conversation_id,
        "created_at": memory.created_at,
    }


@router.get("/memories/{user_id}")
async def list_memories(
    user_id: int,
    service: MemoryService = Depends(get_memory_service),
) -> dict[str, Any]:
    """List test memories for one user."""
    memories = await service.list_user_memories(user_id=user_id)

    return {
        "user_id": user_id,
        "memories": [
            {
                "id": memory.id,
                "memory_type": memory.memory_type,
                "content": memory.content,
                "source_conversation_id": memory.source_conversation_id,
                "created_at": memory.created_at,
            }
            for memory in memories
        ],
    }


@router.post("/widgets")
async def create_widget(
    request: CreateWidgetRequest,
    service: WidgetService = Depends(get_widget_service),
) -> dict[str, Any]:
    """Create a test widget config."""
    widget = await service.create_widget_config(
        actor_id=request.actor_id,
        allowed_origins=request.allowed_origins,
        theme=request.theme,
        greeting=request.greeting,
        enabled_tools=request.enabled_tools,
    )

    return {
        "id": widget.id,
        "public_widget_id": widget.public_widget_id,
        "allowed_origins": widget.allowed_origins,
        "theme": widget.theme,
        "greeting": widget.greeting,
        "enabled_tools": widget.enabled_tools,
        "is_active": widget.is_active,
    }


@router.get("/widgets")
async def list_widgets(
    service: WidgetService = Depends(get_widget_service),
) -> dict[str, Any]:
    """List test widget configs."""
    widgets = await service.list_widget_configs()

    return {
        "widgets": [
            {
                "id": widget.id,
                "public_widget_id": widget.public_widget_id,
                "allowed_origins": widget.allowed_origins,
                "theme": widget.theme,
                "greeting": widget.greeting,
                "enabled_tools": widget.enabled_tools,
                "is_active": widget.is_active,
            }
            for widget in widgets
        ],
    }


@router.get("/widgets/{public_widget_id}")
async def get_widget(
    public_widget_id: str,
    service: WidgetService = Depends(get_widget_service),
) -> dict[str, Any]:
    """Fetch one test widget config."""
    widget = await service.get_widget_config(public_widget_id=public_widget_id)

    return {
        "id": widget.id,
        "public_widget_id": widget.public_widget_id,
        "allowed_origins": widget.allowed_origins,
        "theme": widget.theme,
        "greeting": widget.greeting,
        "enabled_tools": widget.enabled_tools,
        "is_active": widget.is_active,
    }