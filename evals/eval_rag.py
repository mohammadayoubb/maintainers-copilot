"""RAG evaluation script for the Maintainer's Copilot.

This script evaluates retrieval quality against the RAG golden set.

Current retrieval metrics:
- hit@5
- MRR@10

This version uses the same MiniLM embedding file used by RagService.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rag.build_embeddings import load_embeddings
from rag.embeddings import build_embedder
from rag.ingest import DEFAULT_CHUNKS_PATH, load_chunks_jsonl
from rag.pipeline import build_local_rag_pipeline


GOLDEN_PATH = Path("evals/golden/rag_golden.jsonl")
REPORT_PATH = Path("evals/eval_report.json")

EMBEDDING_MODEL_NAME = "BAAI/bge-small-en"
DEFAULT_EMBEDDINGS_PATH = Path(
    "rag/data/embeddings_BAAI_bge-small-en.jsonl"
)


@dataclass(frozen=True)
class RagGoldenExample:
    """One RAG golden-set example."""

    example_id: str
    question: str
    ideal_answer: str
    ground_truth_chunks: list[str]


@dataclass(frozen=True)
class RagEvalResult:
    """Metrics for one RAG eval run."""

    total_examples: int
    hit_at_5: float
    mrr_at_10: float
    skipped_examples: int


def load_rag_golden_set(path: Path = GOLDEN_PATH) -> list[RagGoldenExample]:
    """Load the RAG golden set from JSONL."""

    examples: list[RagGoldenExample] = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            row = json.loads(line)
            _validate_golden_row(row, line_number)

            examples.append(
                RagGoldenExample(
                    example_id=str(row["id"]),
                    question=str(row["question"]),
                    ideal_answer=str(row["ideal_answer"]),
                    ground_truth_chunks=list(row["ground_truth_chunks"]),
                )
            )

    return examples


def evaluate_retrieval(
    *,
    examples: list[RagGoldenExample],
    retrieved_chunk_ids_by_example: dict[str, list[str]],
) -> RagEvalResult:
    """Calculate hit@5 and MRR@10 for retrieved chunk IDs."""

    if not examples:
        return RagEvalResult(
            total_examples=0,
            hit_at_5=0.0,
            mrr_at_10=0.0,
            skipped_examples=0,
        )

    hit_total = 0.0
    reciprocal_rank_total = 0.0
    skipped_examples = 0

    for example in examples:
        retrieved_ids = retrieved_chunk_ids_by_example.get(example.example_id, [])

        if _has_placeholder_ground_truth(example):
            skipped_examples += 1
            continue

        relevant_ids = set(example.ground_truth_chunks)

        if any(chunk_id in relevant_ids for chunk_id in retrieved_ids[:5]):
            hit_total += 1.0

        reciprocal_rank_total += _reciprocal_rank(
            retrieved_ids=retrieved_ids[:10],
            relevant_ids=relevant_ids,
        )

    evaluated_count = len(examples) - skipped_examples

    if evaluated_count == 0:
        return RagEvalResult(
            total_examples=len(examples),
            hit_at_5=0.0,
            mrr_at_10=0.0,
            skipped_examples=skipped_examples,
        )

    return RagEvalResult(
        total_examples=len(examples),
        hit_at_5=hit_total / evaluated_count,
        mrr_at_10=reciprocal_rank_total / evaluated_count,
        skipped_examples=skipped_examples,
    )


def run_local_retrieval_eval(
    *,
    golden_path: Path = GOLDEN_PATH,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    embeddings_path: Path = DEFAULT_EMBEDDINGS_PATH,
) -> RagEvalResult:
    """Run retrieval eval using local chunks and MiniLM embeddings."""

    examples = load_rag_golden_set(golden_path)
    chunks = load_chunks_jsonl(chunks_path)

    if not chunks:
        return RagEvalResult(
            total_examples=len(examples),
            hit_at_5=0.0,
            mrr_at_10=0.0,
            skipped_examples=len(
                [item for item in examples if _has_placeholder_ground_truth(item)]
            ),
        )

    if not embeddings_path.exists():
        raise FileNotFoundError(
            f"Embeddings file not found: {embeddings_path}. "
            "Run python rag/build_embeddings.py --backend sentence-transformers "
            "--model-name BAAI/bge-small-en first."
        )

    chunk_embeddings = load_embeddings(embeddings_path)
    embedder = build_embedder(EMBEDDING_MODEL_NAME)

    pipeline = build_local_rag_pipeline(
        chunks=chunks,
        chunk_embeddings=chunk_embeddings,
        retrieval_top_k=20,
        rerank_top_k=10,
    )

    retrieved_chunk_ids_by_example: dict[str, list[str]] = {}

    for example in examples:
        query_embedding = embedder.encode([example.question])[0]

        result = pipeline.retrieve(
            question=example.question,
            query_embedding=query_embedding,
        )

        retrieved_chunk_ids_by_example[example.example_id] = [
            item.chunk.chunk_id for item in result.final_chunks
        ]

    return evaluate_retrieval(
        examples=examples,
        retrieved_chunk_ids_by_example=retrieved_chunk_ids_by_example,
    )


def save_rag_eval_report(result: RagEvalResult, path: Path = REPORT_PATH) -> None:
    """Merge RAG metrics into eval_report.json."""

    existing_report: dict[str, Any] = {}

    if path.exists():
        existing_report = json.loads(path.read_text(encoding="utf-8"))

    existing_report["rag"] = {
        "total_examples": result.total_examples,
        "hit_at_5": result.hit_at_5,
        "mrr_at_10": result.mrr_at_10,
        "skipped_examples": result.skipped_examples,
        "embedding_model": EMBEDDING_MODEL_NAME,
        "embeddings_file": str(DEFAULT_EMBEDDINGS_PATH),
    }

    path.write_text(
        json.dumps(existing_report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _validate_golden_row(row: dict[str, Any], line_number: int) -> None:
    """Validate one RAG golden-set row."""

    required_keys = {"id", "question", "ideal_answer", "ground_truth_chunks"}
    missing = required_keys - set(row)

    if missing:
        raise ValueError(f"Line {line_number} missing keys: {missing}")

    if not isinstance(row["ground_truth_chunks"], list):
        raise TypeError(f"Line {line_number} ground_truth_chunks must be a list.")


def _reciprocal_rank(*, retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    """Return reciprocal rank of the first relevant retrieved chunk."""

    for index, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in relevant_ids:
            return 1.0 / index

    return 0.0


def _has_placeholder_ground_truth(example: RagGoldenExample) -> bool:
    """Check whether the example still needs real chunk IDs."""

    return any(
        chunk_id.startswith("TODO_REPLACE_WITH_REAL_CHUNK_ID")
        for chunk_id in example.ground_truth_chunks
    )


def main() -> None:
    """Run RAG eval and write eval_report.json."""

    result = run_local_retrieval_eval()
    save_rag_eval_report(result)

    print("RAG eval complete")
    print(f"total_examples={result.total_examples}")
    print(f"hit@5={result.hit_at_5:.4f}")
    print(f"mrr@10={result.mrr_at_10:.4f}")
    print(f"skipped_examples={result.skipped_examples}")


if __name__ == "__main__":
    main()