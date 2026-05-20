"""RAG service for the Maintainer's Copilot.

This service owns the business-level RAG flow.

Architecture rule:
- API routes should not call the RAG pipeline directly.
- API routes should call this service.
- This service coordinates retrieval, formatting, and error handling.

For now, this service uses saved local chunks and saved local embeddings.
Later, the embedding file can be replaced by real sentence-transformer
embeddings or pgvector without changing the API route shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.domain.errors import ToolFailureError
from rag.build_embeddings import load_embeddings
from rag.ingest import load_chunks_jsonl
from rag.pipeline import (
    RagPipelineResult,
    build_local_rag_pipeline,
    format_chunks_for_prompt,
    get_grounding_chunk_ids,
)


DEFAULT_EMBEDDINGS_PATH = Path("rag/data/embeddings_simple.jsonl")


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
        except ToolFailureError:
            raise
        except Exception as exc:
            raise ToolFailureError("RAG retrieval failed.") from exc

        return RagAnswerResponse(
            question=request.question,
            rewritten_query=result.rewritten_query,
            grounding_chunk_ids=get_grounding_chunk_ids(result),
            context=format_chunks_for_prompt(result.final_chunks),
        )

    def _run_local_pipeline(self, request: RagAnswerRequest) -> RagPipelineResult:
        """Run the local RAG pipeline using saved chunks and embeddings."""

        chunks = load_chunks_jsonl()

        if not chunks:
            raise ToolFailureError(
                "No RAG chunks were found. Run the RAG ingestion pipeline first."
            )

        if not DEFAULT_EMBEDDINGS_PATH.exists():
            raise ToolFailureError(
                "No RAG embeddings were found. Run python rag/build_embeddings.py first."
            )

        chunk_embeddings = load_embeddings(DEFAULT_EMBEDDINGS_PATH)

        missing_embedding_ids = [
            chunk.chunk_id
            for chunk in chunks
            if chunk.chunk_id not in chunk_embeddings
        ]

        if missing_embedding_ids:
            raise ToolFailureError(
                "Some RAG chunks are missing embeddings. Rebuild the embedding file."
            )

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
    """Create a deterministic query embedding for the current simple backend.

    This must match the simple embedding logic used by rag/build_embeddings.py.
    It will be replaced once the service uses a real embedding model for both
    chunks and queries.
    """

    vector = [0.0] * dimensions

    for index, character in enumerate(text.lower()):
        vector[index % dimensions] += ord(character) / 1000.0

    return vector