"""Reranking utilities for the Maintainer's Copilot RAG pipeline.

Hybrid retrieval gives us a good candidate set, but the project also requires
cross-encoder reranking. A cross-encoder looks at the query and chunk text
together, then gives a more precise relevance score.

Pipeline position:

query
  -> hybrid retrieval top 20
  -> cross-encoder reranking
  -> final top 5 chunks
  -> LLM answer
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from rag.retrieval import RetrievedChunk


DEFAULT_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class Reranker(Protocol):
    """Protocol for reranking retrieved chunks."""

    def rerank(
        self,
        *,
        query: str,
        retrieved_chunks: list[RetrievedChunk],
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """Return retrieved chunks reordered by reranker relevance."""


@dataclass(frozen=True)
class RerankerConfig:
    """Configuration for the cross-encoder reranker."""

    model_name: str = DEFAULT_RERANKER_MODEL
    max_length: int = 512


class CrossEncoderReranker:
    """Cross-encoder based reranker.

    The import happens inside __init__ so this file remains importable even in
    lightweight environments where sentence-transformers is not installed yet.
    """

    def __init__(self, config: RerankerConfig | None = None) -> None:
        self.config = config or RerankerConfig()

        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is required for cross-encoder reranking. "
                "Install it before running the full RAG pipeline."
            ) from exc

        self._model = CrossEncoder(
            self.config.model_name,
            max_length=self.config.max_length,
        )

    def rerank(
        self,
        *,
        query: str,
        retrieved_chunks: list[RetrievedChunk],
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """Rerank retrieved chunks using cross-encoder relevance scores."""

        if not retrieved_chunks:
            return []

        pairs = [(query, item.chunk.text) for item in retrieved_chunks]
        scores = self._model.predict(pairs)

        reranked: list[RetrievedChunk] = []

        for item, score in zip(retrieved_chunks, scores):
            reranked.append(
                RetrievedChunk(
                    chunk=item.chunk,
                    score=float(score),
                    dense_score=item.dense_score,
                    sparse_score=item.sparse_score,
                )
            )

        return sorted(reranked, key=lambda item: item.score, reverse=True)[:top_k]


class ScoreOnlyReranker:
    """Simple fallback reranker for tests and offline development.

    This does not replace the required cross-encoder in the final system.
    It simply preserves the current retrieval order when we want a fast local
    test without downloading a model.
    """

    def rerank(
        self,
        *,
        query: str,
        retrieved_chunks: list[RetrievedChunk],
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """Return chunks ordered by their existing retrieval score."""

        _ = query

        return sorted(
            retrieved_chunks,
            key=lambda item: item.score,
            reverse=True,
        )[:top_k]


def build_reranker(*, use_cross_encoder: bool = True) -> Reranker:
    """Build the reranker used by the RAG pipeline.

    Args:
        use_cross_encoder: When True, use the required cross-encoder reranker.
            When False, use the lightweight score-only reranker for tests.
    """

    if use_cross_encoder:
        return CrossEncoderReranker()

    return ScoreOnlyReranker()