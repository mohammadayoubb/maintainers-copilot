"""RAG service for the Maintainer's Copilot.

This service owns the business-level RAG flow.

Architecture rule:
- API routes should not call the RAG pipeline directly.
- API routes should call this service.
- This service coordinates retrieval, formatting, and error handling.

This version uses the best Day 3 retrieval configuration measured on the
25-example RAG golden set:

- Embedding model: BAAI/bge-small-en
- Dense weight: 0.8
- Sparse weight: 0.2
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.domain.errors import ToolFailureError
from rag.build_embeddings import load_embeddings
from rag.embeddings import build_embedder
from rag.ingest import load_chunks_jsonl
from rag.pipeline import (
    RagPipelineResult,
    build_local_rag_pipeline,
    format_chunks_for_prompt,
    get_grounding_chunk_ids,
)


EMBEDDING_MODEL_NAME = "BAAI/bge-small-en"
DEFAULT_EMBEDDINGS_PATH = Path("rag/data/embeddings_BAAI_bge-small-en.jsonl")

DENSE_WEIGHT = 0.8
SPARSE_WEIGHT = 0.2


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
        """Retrieve grounding chunks for a maintainer question."""

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
        """Run the local RAG pipeline using saved BGE embeddings."""

        chunks = load_chunks_jsonl()

        if not chunks:
            raise ToolFailureError(
                "No RAG chunks were found. Run the RAG ingestion pipeline first."
            )

        if not DEFAULT_EMBEDDINGS_PATH.exists():
            raise ToolFailureError(
                "No BGE RAG embeddings were found. "
                "Run: python rag/build_embeddings.py "
                "--backend sentence-transformers --model-name BAAI/bge-small-en"
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

        query_embedding = build_embedder(EMBEDDING_MODEL_NAME).encode([request.question])[0]

        pipeline = build_local_rag_pipeline(
            chunks=chunks,
            chunk_embeddings=chunk_embeddings,
            retrieval_top_k=20,
            rerank_top_k=5,
            dense_weight=DENSE_WEIGHT,
            sparse_weight=SPARSE_WEIGHT,
        )

        return pipeline.retrieve(
            question=request.question,
            query_embedding=query_embedding,
            metadata_filter=request.metadata_filter,
        )
