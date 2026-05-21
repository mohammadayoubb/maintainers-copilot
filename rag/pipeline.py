"""End-to-end RAG pipeline for the Maintainer's Copilot.

This module connects query transformation, hybrid retrieval, metadata filtering,
and reranking into one reusable pipeline.

The chatbot's rag_answer tool can call this pipeline later through a service.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rag.chunking import RagChunk
from rag.query_transform import QueryTransformResult, transform_query
from rag.rerank import Reranker, ScoreOnlyReranker
from rag.retrieval import RetrievedChunk, hybrid_retrieve


@dataclass(frozen=True)
class RagPipelineConfig:
    """Configuration for one RAG retrieval run."""

    dense_weight: float = 0.8
    sparse_weight: float = 0.2
    retrieval_top_k: int = 20
    rerank_top_k: int = 5


@dataclass(frozen=True)
class RagPipelineResult:
    """Result returned by the RAG pipeline before answer generation."""

    original_query: str
    rewritten_query: str
    added_query_terms: list[str]
    retrieved_chunks: list[RetrievedChunk]
    final_chunks: list[RetrievedChunk]
    metadata_filter: dict[str, Any] | None = None


@dataclass
class RagPipeline:
    """Local RAG retrieval pipeline.

    This version assumes chunks and embeddings are already loaded in memory.
    Later, the same shape can be backed by pgvector/Qdrant without changing
    the API layer or chatbot tool interface.
    """

    chunks: list[RagChunk]
    chunk_embeddings: dict[str, list[float]]
    reranker: Reranker = field(default_factory=ScoreOnlyReranker)
    config: RagPipelineConfig = field(default_factory=RagPipelineConfig)

    def retrieve(
        self,
        *,
        question: str,
        query_embedding: list[float],
        metadata_filter: dict[str, Any] | None = None,
    ) -> RagPipelineResult:
        """Run query transformation, hybrid retrieval, and reranking."""

        transformed_query = transform_query(question)

        retrieved_chunks = hybrid_retrieve(
            query=transformed_query.rewritten_query,
            query_embedding=query_embedding,
            chunks=self.chunks,
            chunk_embeddings=self.chunk_embeddings,
            dense_weight=self.config.dense_weight,
            sparse_weight=self.config.sparse_weight,
            top_k=self.config.retrieval_top_k,
            metadata_filter=metadata_filter,
        )

        final_chunks = self.reranker.rerank(
            query=transformed_query.rewritten_query,
            retrieved_chunks=retrieved_chunks,
            top_k=self.config.rerank_top_k,
        )

        return RagPipelineResult(
            original_query=question,
            rewritten_query=transformed_query.rewritten_query,
            added_query_terms=transformed_query.added_terms,
            retrieved_chunks=retrieved_chunks,
            final_chunks=final_chunks,
            metadata_filter=metadata_filter,
        )


def format_chunks_for_prompt(chunks: list[RetrievedChunk]) -> str:
    """Format retrieved chunks so they can be safely inserted into a RAG prompt."""

    formatted_chunks: list[str] = []

    for index, item in enumerate(chunks, start=1):
        chunk = item.chunk
        source = chunk.metadata.get("url") or chunk.metadata.get("document_id") or chunk.chunk_id

        formatted_chunks.append(
            "\n".join(
                [
                    f"[Chunk {index}]",
                    f"chunk_id: {chunk.chunk_id}",
                    f"source_type: {chunk.source_type}",
                    f"title: {chunk.title}",
                    f"source: {source}",
                    f"score: {item.score:.4f}",
                    "text:",
                    chunk.text,
                ]
            )
        )

    return "\n\n---\n\n".join(formatted_chunks)


def get_grounding_chunk_ids(result: RagPipelineResult) -> list[str]:
    """Return final chunk IDs used for grounding an answer."""

    return [item.chunk.chunk_id for item in result.final_chunks]


def build_local_rag_pipeline(
    *,
    chunks: list[RagChunk],
    chunk_embeddings: dict[str, list[float]],
    dense_weight: float = 0.8,
    sparse_weight: float = 0.2,
    retrieval_top_k: int = 20,
    rerank_top_k: int = 5,
    reranker: Reranker | None = None,
) -> RagPipeline:
    """Build a local RAG pipeline with explicit retrieval settings."""

    return RagPipeline(
        chunks=chunks,
        chunk_embeddings=chunk_embeddings,
        reranker=reranker or ScoreOnlyReranker(),
        config=RagPipelineConfig(
            dense_weight=dense_weight,
            sparse_weight=sparse_weight,
            retrieval_top_k=retrieval_top_k,
            rerank_top_k=rerank_top_k,
        ),
    )