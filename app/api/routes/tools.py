"""Tool API routes.

This file exposes simple HTTP endpoints for chatbot tools.

These endpoints will later be used by the chatbot tool-calling layer.

Important architecture rule:
Routes should handle HTTP input/output only.
Tool business logic should live in services.
External communication should live in infra adapters.
"""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.infra.model_client import extract_entities, summarize_thread
from app.services.rag_service import RagAnswerRequest, RagService

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


class RagApiRequest(BaseModel):
    """Request body for retrieving grounded RAG context."""

    question: str = Field(..., min_length=1)
    metadata_filter: dict[str, Any] | None = None


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


@router.post("/rag")
async def rag_endpoint(request: RagApiRequest) -> dict[str, Any]:
    """Retrieve grounded context for a maintainer question.

    This route does not run retrieval directly. It delegates to RagService,
    keeping HTTP concerns in the API layer and RAG logic in the service layer.
    """

    service = RagService()
    response = service.retrieve_context(
        RagAnswerRequest(
            question=request.question,
            metadata_filter=request.metadata_filter,
        )
    )

    return {
        "question": response.question,
        "rewritten_query": response.rewritten_query,
        "grounding_chunk_ids": response.grounding_chunk_ids,
        "context": response.context,
    }