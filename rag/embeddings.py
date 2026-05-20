"""Embedding utilities for the Maintainer's Copilot RAG pipeline.

This file owns text embedding generation for documentation chunks and resolved
issue chunks.

Day 3 requires comparing at least two embedding models. This module makes that
easy by keeping the model name configurable instead of hardcoding one model
throughout the RAG pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


DEFAULT_EMBEDDING_MODELS = [
    "BAAI/bge-small-en",
    "sentence-transformers/all-MiniLM-L6-v2",
]


class EmbeddingModel(Protocol):
    """Protocol for any embedding backend used by the RAG pipeline.

    A protocol lets us swap the implementation later without changing retrieval
    code. For example, we can use sentence-transformers locally now, then replace
    it with an API-based embedding provider later if needed.
    """

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""


@dataclass(frozen=True)
class EmbeddingConfig:
    """Configuration for one embedding experiment."""

    model_name: str
    normalize_embeddings: bool = True
    batch_size: int = 32


class SentenceTransformerEmbedder:
    """Sentence-transformers based embedding adapter.

    The import happens inside __init__ so the rest of the app can still import
    this file even if sentence-transformers is not installed in a lightweight
    environment.
    """

    def __init__(self, config: EmbeddingConfig) -> None:
        self.config = config

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is required for local embeddings. "
                "Install it before running the RAG embedding pipeline."
            ) from exc

        self._model = SentenceTransformer(config.model_name)

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts using the configured sentence-transformer."""

        if not texts:
            return []

        embeddings = self._model.encode(
            texts,
            batch_size=self.config.batch_size,
            normalize_embeddings=self.config.normalize_embeddings,
            show_progress_bar=False,
        )

        return embeddings.tolist()


def get_embedding_configs() -> list[EmbeddingConfig]:
    """Return the embedding models we will compare for the RAG decision.

    Later, evals/eval_rag.py will run retrieval against these configs and record
    hit@5 and MRR@10 so the final embedding choice is backed by numbers.
    """

    return [EmbeddingConfig(model_name=model_name) for model_name in DEFAULT_EMBEDDING_MODELS]


def build_embedder(model_name: str) -> SentenceTransformerEmbedder:
    """Create an embedder for one model name."""

    return SentenceTransformerEmbedder(EmbeddingConfig(model_name=model_name))


def cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    This is useful for local tests and simple dense retrieval. Production vector
    search can later move to pgvector or Qdrant, but the math stays the same.
    """

    if len(vector_a) != len(vector_b):
        raise ValueError("Vectors must have the same length.")

    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
    norm_a = sum(a * a for a in vector_a) ** 0.5
    norm_b = sum(b * b for b in vector_b) ** 0.5

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)