"""Build embeddings for RAG chunks.

This script reads chunks from rag/data/chunks.jsonl and writes one embedding
vector per chunk.

It supports two backends:

1. simple
   A deterministic lightweight embedding used only for local tests.

2. sentence-transformers
   A real embedding backend used for the final RAG pipeline and embedding
   model comparison.

Example test run:
    python rag/build_embeddings.py --backend simple

Example real run:
    python rag/build_embeddings.py --backend sentence-transformers --model-name BAAI/bge-small-en
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rag.embeddings import build_embedder
from rag.ingest import DEFAULT_CHUNKS_PATH, load_chunks_jsonl


DEFAULT_OUTPUT_DIR = Path("rag/data")


def build_embeddings(
    *,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    backend: str = "simple",
    model_name: str = "simple",
) -> Path:
    """Build embeddings for all saved RAG chunks."""

    chunks = load_chunks_jsonl(chunks_path)

    if not chunks:
        raise RuntimeError(
            f"No chunks found at {chunks_path}. Run python rag/ingest.py first."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"embeddings_{_safe_model_name(model_name)}.jsonl"

    texts = [chunk.text for chunk in chunks]

    if backend == "simple":
        vectors = [_simple_text_embedding(text) for text in texts]
    elif backend == "sentence-transformers":
        embedder = build_embedder(model_name)
        vectors = embedder.encode(texts)
    else:
        raise ValueError(
            "Unsupported backend. Use 'simple' or 'sentence-transformers'."
        )

    with output_path.open("w", encoding="utf-8") as file:
        for chunk, vector in zip(chunks, vectors):
            row = {
                "chunk_id": chunk.chunk_id,
                "embedding_model": model_name,
                "backend": backend,
                "embedding": vector,
            }
            file.write(json.dumps(row, ensure_ascii=False) + "\n")

    return output_path


def load_embeddings(path: Path) -> dict[str, list[float]]:
    """Load embeddings from a JSONL file into a chunk_id -> vector dictionary."""

    embeddings: dict[str, list[float]] = {}

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            row = json.loads(line)

            if "chunk_id" not in row or "embedding" not in row:
                raise ValueError(f"Invalid embedding row on line {line_number}.")

            embeddings[str(row["chunk_id"])] = [float(value) for value in row["embedding"]]

    return embeddings


def _simple_text_embedding(text: str, dimensions: int = 32) -> list[float]:
    """Create a deterministic test embedding.

    This is only for local tests. It is not the final RAG embedding model.
    """

    vector = [0.0] * dimensions

    for index, character in enumerate(text.lower()):
        vector[index % dimensions] += ord(character) / 1000.0

    return vector


def _safe_model_name(model_name: str) -> str:
    """Convert a model name into a safe filename component."""

    return (
        model_name.replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
        .replace(" ", "_")
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description="Build RAG chunk embeddings.")
    parser.add_argument(
        "--chunks-path",
        type=Path,
        default=DEFAULT_CHUNKS_PATH,
        help="Path to rag chunks JSONL.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where embeddings JSONL will be written.",
    )
    parser.add_argument(
        "--backend",
        choices=["simple", "sentence-transformers"],
        default="simple",
        help="Embedding backend to use.",
    )
    parser.add_argument(
        "--model-name",
        default="simple",
        help="Embedding model name.",
    )

    return parser.parse_args()


def main() -> None:
    """Build embeddings from command-line arguments."""

    args = parse_args()

    output_path = build_embeddings(
        chunks_path=args.chunks_path,
        output_dir=args.output_dir,
        backend=args.backend,
        model_name=args.model_name,
    )

    print(f"Saved embeddings to {output_path}")


if __name__ == "__main__":
    main()