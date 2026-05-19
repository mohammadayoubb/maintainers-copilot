"""Tool API routes.

This file exposes simple HTTP endpoints for model-server tools.

These endpoints will later be used by the chatbot tool-calling layer.

Important architecture rule:
Routes should handle HTTP input/output only.
The actual model-server communication is handled through app.infra.model_client.
"""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.infra.model_client import extract_entities, summarize_thread

# All routes in this file are grouped under /tools.
router = APIRouter(prefix="/tools", tags=["tools"])


class NerApiRequest(BaseModel):
    """Request body for extracting code-shaped entities."""

    text: str = Field(..., min_length=1)


class SummarizeApiRequest(BaseModel):
    """Request body for summarizing an issue thread."""

    title: str = Field(..., min_length=1)
    body: str | None = None
    comments: list[str] = Field(default_factory=list)


@router.post("/ner")
async def ner_endpoint(request: NerApiRequest) -> dict[str, Any]:
    """Extract code-shaped entities from text.

    This route calls the model-server /ner endpoint through the model client.
    """
    return extract_entities(text=request.text)


@router.post("/summarize")
async def summarize_endpoint(request: SummarizeApiRequest) -> dict[str, Any]:
    """Summarize an issue thread.

    This route calls the model-server /summarize endpoint through the model client.
    """
    return summarize_thread(
        title=request.title,
        body=request.body,
        comments=request.comments,
    )