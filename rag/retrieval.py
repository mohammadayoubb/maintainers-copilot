"""Retrieval utilities for the Maintainer's Copilot RAG pipeline.

This module implements the core retrieval strategies required for Day 3:

1. Dense retrieval using embedding similarity.
2. Sparse retrieval using keyword overlap.
3. Hybrid retrieval combining dense and sparse scores.
4. Metadata filtering for source type, labels, issue numbers, and other fields.

The first version is intentionally local and testable. Later, the same service
logic can be backed by pgvector or another vector store without changing the
high-level retrieval flow.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

from rag.chunking import RagChunk
from rag.embeddings import cosine_similarity


@dataclass(frozen=True)
class RetrievedChunk:
    """A chunk returned by a retrieval strategy."""

    chunk: RagChunk
    score: float
    dense_score: float = 0.0
    sparse_score: float = 0.0


def tokenize_for_sparse_search(text: str) -> list[str]:
    """Convert text into simple lowercase search tokens.

    This is a lightweight sparse retriever. It keeps code-shaped words useful
    for GitHub issues, such as read_csv, DataFrame, ValueError, and file names.
    """

    return re.findall(r"[a-zA-Z0-9_./:-]+", text.lower())


def sparse_score(query: str, chunk_text: str) -> float:
    """Score a chunk by normalized keyword overlap with the query."""

    query_tokens = tokenize_for_sparse_search(query)
    chunk_tokens = tokenize_for_sparse_search(chunk_text)

    if not query_tokens or not chunk_tokens:
        return 0.0

    query_counts = _token_counts(query_tokens)
    chunk_counts = _token_counts(chunk_tokens)

    overlap = 0.0

    for token, query_count in query_counts.items():
        if token in chunk_counts:
            overlap += min(query_count, chunk_counts[token])

    return overlap / math.sqrt(len(query_tokens) * len(chunk_tokens))


def dense_retrieve(
    *,
    query_embedding: list[float],
    chunks: list[RagChunk],
    chunk_embeddings: dict[str, list[float]],
    top_k: int = 10,
    metadata_filter: dict[str, Any] | None = None,
) -> list[RetrievedChunk]:
    """Return chunks ranked by cosine similarity to the query embedding."""

    filtered_chunks = filter_chunks_by_metadata(chunks, metadata_filter)
    results: list[RetrievedChunk] = []

    for chunk in filtered_chunks:
        embedding = chunk_embeddings.get(chunk.chunk_id)

        if embedding is None:
            continue

        score = cosine_similarity(query_embedding, embedding)
        results.append(
            RetrievedChunk(
                chunk=chunk,
                score=score,
                dense_score=score,
                sparse_score=0.0,
            )
        )

    return sorted(results, key=lambda item: item.score, reverse=True)[:top_k]


def sparse_retrieve(
    *,
    query: str,
    chunks: list[RagChunk],
    top_k: int = 10,
    metadata_filter: dict[str, Any] | None = None,
) -> list[RetrievedChunk]:
    """Return chunks ranked by sparse keyword overlap."""

    filtered_chunks = filter_chunks_by_metadata(chunks, metadata_filter)
    results: list[RetrievedChunk] = []

    for chunk in filtered_chunks:
        score = sparse_score(query, chunk.text)

        if score <= 0:
            continue

        results.append(
            RetrievedChunk(
                chunk=chunk,
                score=score,
                dense_score=0.0,
                sparse_score=score,
            )
        )

    return sorted(results, key=lambda item: item.score, reverse=True)[:top_k]


def hybrid_retrieve(
    *,
    query: str,
    query_embedding: list[float],
    chunks: list[RagChunk],
    chunk_embeddings: dict[str, list[float]],
    dense_weight: float = 0.7,
    sparse_weight: float = 0.3,
    top_k: int = 10,
    metadata_filter: dict[str, Any] | None = None,
) -> list[RetrievedChunk]:
    """Combine dense and sparse retrieval scores.

    The project requires hybrid retrieval with tuned weighting. This function
    accepts weights so evals can test combinations such as:

    - 0.5 dense / 0.5 sparse
    - 0.7 dense / 0.3 sparse
    - 0.8 dense / 0.2 sparse
    """

    if dense_weight < 0 or sparse_weight < 0:
        raise ValueError("Retrieval weights must be non-negative.")

    if dense_weight == 0 and sparse_weight == 0:
        raise ValueError("At least one retrieval weight must be greater than zero.")

    filtered_chunks = filter_chunks_by_metadata(chunks, metadata_filter)
    results: list[RetrievedChunk] = []

    for chunk in filtered_chunks:
        embedding = chunk_embeddings.get(chunk.chunk_id)
        dense = cosine_similarity(query_embedding, embedding) if embedding is not None else 0.0
        sparse = sparse_score(query, chunk.text)

        combined = (dense_weight * dense) + (sparse_weight * sparse)

        results.append(
            RetrievedChunk(
                chunk=chunk,
                score=combined,
                dense_score=dense,
                sparse_score=sparse,
            )
        )

    return sorted(results, key=lambda item: item.score, reverse=True)[:top_k]


def filter_chunks_by_metadata(
    chunks: list[RagChunk],
    metadata_filter: dict[str, Any] | None,
) -> list[RagChunk]:
    """Return chunks that match all requested metadata filters.

    Example filters:
        {"source_type": "docs"}
        {"source_type": "resolved_issue", "labels": "bug"}
        {"issue_number": 123}
    """

    if not metadata_filter:
        return chunks

    filtered: list[RagChunk] = []

    for chunk in chunks:
        if _chunk_matches_filter(chunk, metadata_filter):
            filtered.append(chunk)

    return filtered


def _chunk_matches_filter(chunk: RagChunk, metadata_filter: dict[str, Any]) -> bool:
    """Check if one chunk satisfies a metadata filter."""

    for key, expected_value in metadata_filter.items():
        if key == "source_type":
            actual_value = chunk.source_type
        else:
            actual_value = chunk.metadata.get(key)

        if isinstance(actual_value, list):
            if expected_value not in actual_value:
                return False
        elif actual_value != expected_value:
            return False

    return True


def _token_counts(tokens: list[str]) -> dict[str, int]:
    """Count token frequencies for sparse scoring."""

    counts: dict[str, int] = {}

    for token in tokens:
        counts[token] = counts.get(token, 0) + 1

    return counts