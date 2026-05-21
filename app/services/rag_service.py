"""RAG service for the Maintainer's Copilot.

This service owns the business-level RAG flow.

Architecture rule:
- API routes should not call the RAG pipeline directly.
- API routes should call this service.
- This service coordinates retrieval, formatting, and error handling.

Primary RAG path:
- Embedding model: BAAI/bge-small-en
- Dense weight: 0.8
- Sparse weight: 0.2

Local fallback path:
- If the local API image does not have sentence-transformers installed,
  the service falls back to lightweight keyword retrieval over chunks.jsonl.
- This keeps the chatbot usable during local integration without replacing
  the evaluated Day 3 RAG pipeline.
"""

from __future__ import annotations

import math
import re
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
FALLBACK_TOP_K = 5


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

        The service tries the evaluated embedding-based RAG pipeline first.
        If local embedding dependencies are unavailable, it falls back to
        lightweight sparse retrieval so the chatbot can degrade gracefully.
        """
        try:
            result = self._run_local_pipeline(request)

            return RagAnswerResponse(
                question=request.question,
                rewritten_query=result.rewritten_query,
                grounding_chunk_ids=get_grounding_chunk_ids(result),
                context=format_chunks_for_prompt(result.final_chunks),
            )

        except RuntimeError as exc:
            if "sentence-transformers is required" not in str(exc):
                raise ToolFailureError("RAG retrieval failed.") from exc

            return self._run_sparse_fallback(request)

        except ToolFailureError as exc:
            if "sentence-transformers is required" not in str(exc):
                raise

            return self._run_sparse_fallback(request)

        except Exception as exc:
            raise ToolFailureError("RAG retrieval failed.") from exc

    def _run_local_pipeline(self, request: RagAnswerRequest) -> RagPipelineResult:
        """Run the evaluated local RAG pipeline using saved BGE embeddings."""
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

    def _run_sparse_fallback(self, request: RagAnswerRequest) -> RagAnswerResponse:
        """Run lightweight keyword retrieval when embedding dependencies are missing.

        This fallback is only for local integration and graceful degradation.
        It does not replace the evaluated embedding-based RAG pipeline.
        """
        chunks = load_chunks_jsonl()

        if not chunks:
            raise ToolFailureError(
                "No RAG chunks were found. Run the RAG ingestion pipeline first."
            )

        query_terms = self._tokenize(request.question)

        scored_chunks: list[tuple[float, Any]] = []

        for chunk in chunks:
            if request.metadata_filter and not self._matches_metadata(
                chunk.metadata,
                request.metadata_filter,
            ):
                continue

            chunk_text = self._get_chunk_text(chunk)
            score = self._score_text(query_terms, chunk_text)

            if score > 0:
                scored_chunks.append((score, chunk))

        scored_chunks.sort(key=lambda item: item[0], reverse=True)

        selected_chunks = [chunk for _, chunk in scored_chunks[:FALLBACK_TOP_K]]

        if not selected_chunks:
            selected_chunks = chunks[:FALLBACK_TOP_K]

        return RagAnswerResponse(
            question=request.question,
            rewritten_query=request.question,
            grounding_chunk_ids=[chunk.chunk_id for chunk in selected_chunks],
            context=self._format_fallback_chunks(selected_chunks),
        )

    def _matches_metadata(
        self,
        chunk_metadata: dict[str, Any],
        metadata_filter: dict[str, Any],
    ) -> bool:
        """Return True if a chunk metadata dictionary matches all filter values."""
        for key, expected_value in metadata_filter.items():
            if chunk_metadata.get(key) != expected_value:
                return False

        return True

    def _score_text(self, query_terms: list[str], text: str) -> float:
        """Score a chunk using simple term frequency with length normalization."""
        if not query_terms:
            return 0.0

        text_terms = self._tokenize(text)

        if not text_terms:
            return 0.0

        term_counts: dict[str, int] = {}

        for term in text_terms:
            term_counts[term] = term_counts.get(term, 0) + 1

        raw_score = sum(term_counts.get(term, 0) for term in query_terms)

        return raw_score / math.sqrt(len(text_terms))

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into lowercase keyword terms."""
        return re.findall(r"[a-zA-Z_][a-zA-Z0-9_]+", text.lower())

    def _get_chunk_text(self, chunk: Any) -> str:
        """Read chunk text regardless of the exact chunk field name."""
        if hasattr(chunk, "text"):
            return str(chunk.text)

        if hasattr(chunk, "content"):
            return str(chunk.content)

        if hasattr(chunk, "chunk_text"):
            return str(chunk.chunk_text)

        return str(chunk)

    def _format_fallback_chunks(self, chunks: list[Any]) -> str:
        """Format fallback chunks into grounding context for the chatbot."""
        formatted_chunks: list[str] = []

        for index, chunk in enumerate(chunks, start=1):
            chunk_id = getattr(chunk, "chunk_id", f"chunk_{index}")
            text = self._get_chunk_text(chunk)

            formatted_chunks.append(
                f"[{index}] chunk_id={chunk_id}\n{text[:1200]}"
            )

        return "\n\n".join(formatted_chunks)