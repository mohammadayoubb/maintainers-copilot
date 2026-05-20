"""RAG service for the Maintainer's Copilot.

This service owns the business-level RAG flow.

Architecture rule:
- API routes should not call the RAG pipeline directly.
- API routes should call this service.
- This service coordinates retrieval, formatting, and error handling.

For now, this service uses the local RAG pipeline from rag/pipeline.py.
Later, it can be upgraded to use real embeddings, pgvector, tracing, and LLM
answer generation without changing the API route shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.errors import ToolFailureError
from rag.ingest import load_chunks_jsonl
from rag.pipeline import (
    RagPipelineResult,
    build_local_rag_pipeline,
    format_chunks_for_prompt,
    get_grounding_chunk_ids,
)


@dataclass(frozen=True)
class RagAnswerRequest:
    """Input needed to retrieve grounded context for a maintainer question."""

    question: str
    metadata_filter: dict[str, Any] | None = None


@dataclass(frozen=True)
class RagAnswerResponse:
    """RAG retrieval response before final LLM answer generation."""

    question: str
    rewritten_query: str
    grounding_chunk_ids: list[str]
    context: str


class RagService:
    """Service that coordinates RAG retrieval for the chatbot."""

    def retrieve_context(self, request: RagAnswerRequest) -> RagAnswerResponse:
        """Retrieve grounding chunks for a maintainer question.

        This method currently returns formatted context instead of generating
        the final answer. That keeps Day 3 focused on retrieval quality first.
        """

        try:
            result = self._run_local_pipeline(request)
        except Exception as exc:
            raise ToolFailureError("RAG retrieval failed.") from exc

        return RagAnswerResponse(
            question=request.question,
            rewritten_query=result.rewritten_query,
            grounding_chunk_ids=get_grounding_chunk_ids(result),
            context=format_chunks_for_prompt(result.final_chunks),
        )

    def _run_local_pipeline(self, request: RagAnswerRequest) -> RagPipelineResult:
        """Run the local RAG pipeline using saved chunks."""

        chunks = load_chunks_jsonl()

        if not chunks:
            raise ToolFailureError(
                "No RAG chunks were found. Run the RAG ingestion pipeline first."
            )

        chunk_embeddings = {
            chunk.chunk_id: _simple_text_embedding(chunk.text)
            for chunk in chunks
        }

        pipeline = build_local_rag_pipeline(
            chunks=chunks,
            chunk_embeddings=chunk_embeddings,
            retrieval_top_k=10,
            rerank_top_k=5,
        )

        return pipeline.retrieve(
            question=request.question,
            query_embedding=_simple_text_embedding(request.question),
            metadata_filter=request.metadata_filter,
        )


def _simple_text_embedding(text: str, dimensions: int = 32) -> list[float]:
    """Create a deterministic temporary embedding for local service testing.

    This is not the final embedding model. It keeps the service testable before
    the real embedding comparison and pgvector integration are connected.
    """

    vector = [0.0] * dimensions

    for index, character in enumerate(text.lower()):
        vector[index % dimensions] += ord(character) / 1000.0

    return vector