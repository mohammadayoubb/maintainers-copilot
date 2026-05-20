"""RAG ingestion pipeline for the Maintainer's Copilot.

This module loads documentation files and resolved GitHub issues, then converts
them into structure-aware RAG chunks.

The output chunks can later be embedded, stored in pgvector/Qdrant, evaluated
against the RAG golden set, and used by the chatbot's rag_answer tool.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rag.chunking import RagChunk, chunk_resolved_issue, split_markdown_by_headings


DEFAULT_DOCS_DIR = Path("rag/data/raw_docs")
DEFAULT_RESOLVED_ISSUES_PATH = Path("rag/data/resolved_issues.jsonl")
DEFAULT_CHUNKS_PATH = Path("rag/data/chunks.jsonl")


def load_docs_from_directory(docs_dir: Path = DEFAULT_DOCS_DIR) -> list[RagChunk]:
    """Load markdown docs from a directory and split them into RAG chunks."""

    if not docs_dir.exists():
        return []

    chunks: list[RagChunk] = []

    for file_path in sorted(docs_dir.rglob("*.md")):
        document_id = _stable_document_id(file_path, docs_dir)
        content = file_path.read_text(encoding="utf-8")

        chunks.extend(
            split_markdown_by_headings(
                document_id=document_id,
                title=file_path.stem,
                content=content,
                url=None,
            )
        )

    return chunks


def load_resolved_issue_chunks(
    issues_path: Path = DEFAULT_RESOLVED_ISSUES_PATH,
) -> list[RagChunk]:
    """Load resolved GitHub issues from JSONL and split them into RAG chunks.

    Expected JSONL fields:
        number: int
        title: str
        body: str
        labels: list[str]
        html_url or url: str
        maintainer_comments: list[str]
    """

    if not issues_path.exists():
        return []

    chunks: list[RagChunk] = []

    with issues_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            issue = _parse_json_line(line, line_number)

            chunks.extend(
                chunk_resolved_issue(
                    issue_number=int(issue["number"]),
                    title=str(issue.get("title", "")),
                    body=issue.get("body"),
                    labels=list(issue.get("labels", [])),
                    url=issue.get("html_url") or issue.get("url"),
                    maintainer_comments=list(issue.get("maintainer_comments", [])),
                )
            )

    return chunks


def build_rag_chunks(
    *,
    docs_dir: Path = DEFAULT_DOCS_DIR,
    issues_path: Path = DEFAULT_RESOLVED_ISSUES_PATH,
) -> list[RagChunk]:
    """Build the full RAG chunk list from docs and resolved issues."""

    doc_chunks = load_docs_from_directory(docs_dir)
    issue_chunks = load_resolved_issue_chunks(issues_path)

    return doc_chunks + issue_chunks


def save_chunks_jsonl(chunks: list[RagChunk], output_path: Path = DEFAULT_CHUNKS_PATH) -> None:
    """Save RAG chunks to JSONL so later steps can embed and evaluate them."""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(chunk_to_dict(chunk), ensure_ascii=False) + "\n")


def load_chunks_jsonl(input_path: Path = DEFAULT_CHUNKS_PATH) -> list[RagChunk]:
    """Load previously saved RAG chunks from JSONL."""

    if not input_path.exists():
        return []

    chunks: list[RagChunk] = []

    with input_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            data = _parse_json_line(line, line_number)
            chunks.append(chunk_from_dict(data))

    return chunks


def chunk_to_dict(chunk: RagChunk) -> dict[str, Any]:
    """Convert a RagChunk into a JSON-serializable dictionary."""

    return {
        "chunk_id": chunk.chunk_id,
        "source_type": chunk.source_type,
        "title": chunk.title,
        "text": chunk.text,
        "metadata": chunk.metadata,
    }


def chunk_from_dict(data: dict[str, Any]) -> RagChunk:
    """Convert a dictionary loaded from JSONL into a RagChunk."""

    return RagChunk(
        chunk_id=str(data["chunk_id"]),
        source_type=data["source_type"],
        title=str(data["title"]),
        text=str(data["text"]),
        metadata=dict(data.get("metadata", {})),
    )


def _stable_document_id(file_path: Path, docs_dir: Path) -> str:
    """Create a stable ID from a markdown file path."""

    relative_path = file_path.relative_to(docs_dir)
    raw_id = str(relative_path.with_suffix(""))
    return raw_id.replace("\\", "-").replace("/", "-").replace(" ", "-")


def _parse_json_line(line: str, line_number: int) -> dict[str, Any]:
    """Parse one JSONL line with a helpful error message."""

    try:
        data = json.loads(line)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON on line {line_number}.") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object on line {line_number}.")

    return data


def main() -> None:
    """Build chunks from the default RAG input paths."""

    chunks = build_rag_chunks()
    save_chunks_jsonl(chunks)
    print(f"Saved {len(chunks)} chunks to {DEFAULT_CHUNKS_PATH}")


if __name__ == "__main__":
    main()