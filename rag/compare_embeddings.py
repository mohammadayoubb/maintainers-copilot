
"""Compare RAG embedding models on the golden retrieval set.

This script compares:
1. sentence-transformers/all-MiniLM-L6-v2
2. BAAI/bge-small-en

It uses the existing project retrieval function:
- rag.retrieval.hybrid_retrieve

Metrics:
- hit@5
- MRR@10

Only mapped golden examples are evaluated. Placeholder examples are skipped.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sentence_transformers import SentenceTransformer

from rag.retrieval import hybrid_retrieve


CHUNKS_PATH = Path("rag/data/chunks.jsonl")
GOLDEN_PATH = Path("evals/golden/rag_golden.jsonl")

EMBEDDING_MODELS = [
    "sentence-transformers/all-MiniLM-L6-v2",
    "BAAI/bge-small-en",
]

DENSE_WEIGHT = 0.7
SPARSE_WEIGHT = 0.3


@dataclass(frozen=True)
class CompareChunk:
    """Small chunk object shaped like the chunks expected by retrieval.py."""

    chunk_id: str
    text: str
    source_type: str
    metadata: dict[str, Any]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load a JSONL file into memory."""

    rows: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            rows.append(json.loads(line))

    return rows


def load_chunks(path: Path) -> list[CompareChunk]:
    """Load RAG chunks from JSONL."""

    rows = load_jsonl(path)
    chunks: list[CompareChunk] = []

    for row in rows:
        chunks.append(
            CompareChunk(
                chunk_id=str(row["chunk_id"]),
                text=str(row["text"]),
                source_type=str(row.get("source_type", "unknown")),
                metadata=dict(row.get("metadata", {})),
            )
        )

    return chunks


def get_question(example: dict[str, Any]) -> str:
    """Read the question/query field from a golden example."""

    question = example.get("question") or example.get("query")

    if not question:
        raise ValueError(f"Golden example is missing question/query: {example}")

    return str(question)


def get_ground_truth_chunk_ids(example: dict[str, Any]) -> list[str]:
    """Read expected chunk ids from supported golden formats."""

    if "ground_truth_chunks" in example:
        chunk_ids = example["ground_truth_chunks"]

        if isinstance(chunk_ids, list):
            return [str(chunk_id) for chunk_id in chunk_ids]

        return [str(chunk_ids)]

    if "expected_chunk_id" in example:
        return [str(example["expected_chunk_id"])]

    return []


def is_placeholder_chunk_id(chunk_id: str) -> bool:
    """Check whether a chunk id is still a placeholder."""

    upper_chunk_id = chunk_id.upper()

    return (
        "PLACEHOLDER" in upper_chunk_id
        or "TODO" in upper_chunk_id
        or chunk_id.strip() == ""
    )


def is_mapped_example(example: dict[str, Any]) -> bool:
    """Return True if the example has at least one real ground-truth chunk."""

    chunk_ids = get_ground_truth_chunk_ids(example)

    if not chunk_ids:
        return False

    return any(not is_placeholder_chunk_id(chunk_id) for chunk_id in chunk_ids)


def build_embeddings(
    *,
    model: SentenceTransformer,
    chunks: list[CompareChunk],
) -> dict[str, list[float]]:
    """Create embeddings for all chunk texts using the selected model."""

    texts = [chunk.text for chunk in chunks]
    vectors = model.encode(texts, show_progress_bar=True)

    return {
        chunk.chunk_id: vector.tolist()
        for chunk, vector in zip(chunks, vectors, strict=True)
    }


def hit_at_k(
    *,
    retrieved_chunk_ids: list[str],
    ground_truth_chunk_ids: list[str],
    k: int,
) -> float:
    """Return 1 if any ground-truth chunk appears in the top-k results."""

    top_k_ids = set(retrieved_chunk_ids[:k])
    expected_ids = set(ground_truth_chunk_ids)

    return 1.0 if top_k_ids.intersection(expected_ids) else 0.0


def mrr_at_k(
    *,
    retrieved_chunk_ids: list[str],
    ground_truth_chunk_ids: list[str],
    k: int,
) -> float:
    """Return reciprocal rank for the first matching ground-truth chunk."""

    expected_ids = set(ground_truth_chunk_ids)

    for rank, chunk_id in enumerate(retrieved_chunk_ids[:k], start=1):
        if chunk_id in expected_ids:
            return 1.0 / rank

    return 0.0


def evaluate_model(
    *,
    model_name: str,
    chunks: list[CompareChunk],
    golden_examples: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate one embedding model with the existing hybrid retriever."""

    print(f"\nLoading embedding model: {model_name}")
    model = SentenceTransformer(model_name)

    print(f"Building chunk embeddings for: {model_name}")
    chunk_embeddings = build_embeddings(model=model, chunks=chunks)

    hit_scores: list[float] = []
    mrr_scores: list[float] = []

    for example in golden_examples:
        question = get_question(example)
        ground_truth_chunk_ids = [
            chunk_id
            for chunk_id in get_ground_truth_chunk_ids(example)
            if not is_placeholder_chunk_id(chunk_id)
        ]

        query_embedding = model.encode(question).tolist()

        results = hybrid_retrieve(
            query=question,
            query_embedding=query_embedding,
            chunks=chunks,  # type: ignore[arg-type]
            chunk_embeddings=chunk_embeddings,
            dense_weight=DENSE_WEIGHT,
            sparse_weight=SPARSE_WEIGHT,
            top_k=10,
        )

        retrieved_chunk_ids = [result.chunk.chunk_id for result in results]

        hit_scores.append(
            hit_at_k(
                retrieved_chunk_ids=retrieved_chunk_ids,
                ground_truth_chunk_ids=ground_truth_chunk_ids,
                k=5,
            )
        )

        mrr_scores.append(
            mrr_at_k(
                retrieved_chunk_ids=retrieved_chunk_ids,
                ground_truth_chunk_ids=ground_truth_chunk_ids,
                k=10,
            )
        )

    evaluated_count = len(golden_examples)

    return {
        "model_name": model_name,
        "evaluated_examples": evaluated_count,
        "hit_at_5": sum(hit_scores) / evaluated_count if evaluated_count else 0.0,
        "mrr_at_10": sum(mrr_scores) / evaluated_count if evaluated_count else 0.0,
        "dense_weight": DENSE_WEIGHT,
        "sparse_weight": SPARSE_WEIGHT,
    }


def main() -> None:
    """Run the embedding comparison."""

    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(f"Missing chunks file: {CHUNKS_PATH}")

    if not GOLDEN_PATH.exists():
        raise FileNotFoundError(f"Missing golden file: {GOLDEN_PATH}")

    chunks = load_chunks(CHUNKS_PATH)
    all_examples = load_jsonl(GOLDEN_PATH)
    mapped_examples = [example for example in all_examples if is_mapped_example(example)]

    print(f"Loaded chunks: {len(chunks)}")
    print(f"Total golden examples: {len(all_examples)}")
    print(f"Mapped examples used: {len(mapped_examples)}")
    print(f"Skipped placeholder examples: {len(all_examples) - len(mapped_examples)}")
    print(f"Hybrid weights: dense={DENSE_WEIGHT}, sparse={SPARSE_WEIGHT}")

    if not mapped_examples:
        raise ValueError("No mapped RAG golden examples found.")

    results = [
        evaluate_model(
            model_name=model_name,
            chunks=chunks,
            golden_examples=mapped_examples,
        )
        for model_name in EMBEDDING_MODELS
    ]

    print("\nEmbedding comparison results:")
    for result in results:
        print(
            f"- {result['model_name']}: "
            f"hit@5={result['hit_at_5']:.3f}, "
            f"MRR@10={result['mrr_at_10']:.3f}, "
            f"examples={result['evaluated_examples']}, "
            f"weights={result['dense_weight']}/{result['sparse_weight']}"
        )


if __name__ == "__main__":
    main()
