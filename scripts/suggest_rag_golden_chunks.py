"""Suggest real chunk IDs for the RAG golden set.

The RAG golden set starts with placeholder ground-truth chunk IDs.
This script helps replace those placeholders by retrieving candidate chunks
for each golden question.

Input:
    evals/golden/rag_golden.jsonl
    rag/data/chunks.jsonl
    rag/data/embeddings_simple.jsonl

Output:
    rag/data/rag_golden_suggestions.json

The output is for manual review. We should not blindly trust the suggestions.
A human should inspect the suggested chunks and choose the best ground-truth
chunk IDs for each golden example.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evals.eval_rag import GOLDEN_PATH, RagGoldenExample, load_rag_golden_set
from rag.build_embeddings import load_embeddings
from rag.ingest import DEFAULT_CHUNKS_PATH, load_chunks_jsonl
from rag.pipeline import build_local_rag_pipeline


DEFAULT_EMBEDDINGS_PATH = Path("rag/data/embeddings_simple.jsonl")
DEFAULT_OUTPUT_PATH = Path("rag/data/rag_golden_suggestions.json")


def suggest_chunks_for_golden_set(
    *,
    golden_path: Path = GOLDEN_PATH,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    embeddings_path: Path = DEFAULT_EMBEDDINGS_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    top_k: int = 5,
) -> None:
    """Suggest candidate chunk IDs for each RAG golden-set question."""

    examples = load_rag_golden_set(golden_path)
    chunks = load_chunks_jsonl(chunks_path)

    if not chunks:
        raise RuntimeError(f"No chunks found at {chunks_path}. Run rag/ingest.py first.")

    if not embeddings_path.exists():
        raise RuntimeError(
            f"No embeddings found at {embeddings_path}. "
            "Run rag/build_embeddings.py --backend simple first."
        )

    chunk_embeddings = load_embeddings(embeddings_path)

    pipeline = build_local_rag_pipeline(
        chunks=chunks,
        chunk_embeddings=chunk_embeddings,
        retrieval_top_k=20,
        rerank_top_k=top_k,
    )

    suggestions: list[dict[str, Any]] = []

    for example in examples:
        result = pipeline.retrieve(
            question=example.question,
            query_embedding=_simple_text_embedding(example.question),
        )

        suggestions.append(
            {
                "id": example.example_id,
                "question": example.question,
                "current_ground_truth_chunks": example.ground_truth_chunks,
                "suggested_chunks": [
                    {
                        "rank": rank,
                        "chunk_id": item.chunk.chunk_id,
                        "score": item.score,
                        "title": item.chunk.title,
                        "source_type": item.chunk.source_type,
                        "url": item.chunk.metadata.get("url"),
                        "labels": item.chunk.metadata.get("labels"),
                        "text_preview": item.chunk.text[:500],
                    }
                    for rank, item in enumerate(result.final_chunks, start=1)
                ],
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(suggestions, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote suggestions for {len(suggestions)} golden examples to {output_path}")


def _simple_text_embedding(text: str, dimensions: int = 32) -> list[float]:
    """Create the same deterministic query embedding as the simple backend."""

    vector = [0.0] * dimensions

    for index, character in enumerate(text.lower()):
        vector[index % dimensions] += ord(character) / 1000.0

    return vector


def main() -> None:
    """Run the suggestion script."""

    suggest_chunks_for_golden_set()


if __name__ == "__main__":
    main()