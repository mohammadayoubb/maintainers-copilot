"""Chunking utilities for the Maintainer's Copilot RAG pipeline.

This file is responsible for turning long documentation pages and resolved
GitHub issues into smaller searchable chunks.

We intentionally avoid naive fixed-size chunking only. Instead, we keep useful
structure such as markdown headings, source type, issue number, labels, and URLs.
That metadata will later help retrieval, filtering, reranking, and evaluation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal


SourceType = Literal["docs", "resolved_issue"]


@dataclass(frozen=True)
class RagChunk:
    """A single searchable RAG chunk.

    The chunk_id is stable and human-readable so the golden RAG set can refer
    to exact ground-truth chunks.
    """

    chunk_id: str
    source_type: SourceType
    title: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


def normalize_text(text: str | None) -> str:
    """Normalize whitespace without destroying code-shaped tokens.

    GitHub issues and docs often contain extra blank lines, tabs, or copied
    terminal output. We clean spacing, but we keep the actual words, file names,
    commands, function names, and error messages because they are useful for RAG.
    """

    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_markdown_by_headings(
    *,
    document_id: str,
    title: str,
    content: str,
    url: str | None = None,
    max_chars: int = 1800,
) -> list[RagChunk]:
    """Split markdown documentation using headings as natural boundaries.

    Example:
        # Installation
        text...

        ## Common Errors
        text...

    This produces chunks that remember the heading path. That is better than
    blindly slicing every N characters because retrievers can return a complete
    section with its meaning intact.
    """

    normalized = normalize_text(content)
    if not normalized:
        return []

    lines = normalized.split("\n")
    chunks: list[RagChunk] = []

    current_heading = title
    current_lines: list[str] = []
    chunk_index = 1

    def flush_section() -> None:
        nonlocal chunk_index, current_lines

        section_text = normalize_text("\n".join(current_lines))
        if not section_text:
            current_lines = []
            return

        for part_index, part in enumerate(_split_long_text(section_text, max_chars=max_chars), start=1):
            chunk_id = f"docs-{document_id}-{chunk_index:03d}-{part_index:02d}"
            chunks.append(
                RagChunk(
                    chunk_id=chunk_id,
                    source_type="docs",
                    title=title,
                    text=part,
                    metadata={
                        "heading": current_heading,
                        "url": url,
                        "document_id": document_id,
                        "part": part_index,
                    },
                )
            )

        chunk_index += 1
        current_lines = []

    for line in lines:
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)

        if heading_match:
            flush_section()
            current_heading = heading_match.group(2).strip()
            current_lines.append(line)
        else:
            current_lines.append(line)

    flush_section()
    return chunks


def chunk_resolved_issue(
    *,
    issue_number: int,
    title: str,
    body: str | None,
    labels: list[str],
    url: str | None = None,
    maintainer_comments: list[str] | None = None,
    max_chars: int = 1800,
) -> list[RagChunk]:
    """Create chunks from a resolved GitHub issue.

    We separate the issue description from maintainer answers because these
    serve different retrieval purposes:
    - the title/body explains the problem
    - maintainer comments usually contain the fix, explanation, or resolution
    """

    chunks: list[RagChunk] = []
    maintainer_comments = maintainer_comments or []

    issue_text = normalize_text(f"{title}\n\n{body or ''}")

    if issue_text:
        for part_index, part in enumerate(_split_long_text(issue_text, max_chars=max_chars), start=1):
            chunks.append(
                RagChunk(
                    chunk_id=f"issue-{issue_number}-problem-{part_index:02d}",
                    source_type="resolved_issue",
                    title=title,
                    text=part,
                    metadata={
                        "issue_number": issue_number,
                        "labels": labels,
                        "url": url,
                        "chunk_role": "problem",
                    },
                )
            )

    for comment_index, comment in enumerate(maintainer_comments, start=1):
        comment_text = normalize_text(comment)

        if not comment_text:
            continue

        for part_index, part in enumerate(_split_long_text(comment_text, max_chars=max_chars), start=1):
            chunks.append(
                RagChunk(
                    chunk_id=f"issue-{issue_number}-maintainer-{comment_index:02d}-{part_index:02d}",
                    source_type="resolved_issue",
                    title=title,
                    text=part,
                    metadata={
                        "issue_number": issue_number,
                        "labels": labels,
                        "url": url,
                        "chunk_role": "maintainer_answer",
                        "comment_index": comment_index,
                    },
                )
            )

    return chunks


def _split_long_text(text: str, *, max_chars: int) -> list[str]:
    """Split long text into paragraph-aware pieces.

    This is a fallback splitter used only after we already split by meaningful
    structure such as headings or issue sections.
    """

    normalized = normalize_text(text)

    if len(normalized) <= max_chars:
        return [normalized]

    paragraphs = normalized.split("\n\n")
    parts: list[str] = []
    current = ""

    for paragraph in paragraphs:
        paragraph = paragraph.strip()

        if not paragraph:
            continue

        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph

        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                parts.append(current)

            if len(paragraph) > max_chars:
                parts.extend(_hard_split(paragraph, max_chars=max_chars))
                current = ""
            else:
                current = paragraph

    if current:
        parts.append(current)

    return parts


def _hard_split(text: str, *, max_chars: int) -> list[str]:
    """Last-resort splitter for extremely long paragraphs or stack traces."""

    return [text[i : i + max_chars].strip() for i in range(0, len(text), max_chars)]