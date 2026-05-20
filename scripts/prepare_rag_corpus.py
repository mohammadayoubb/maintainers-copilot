"""Prepare the resolved-issue corpus for the RAG pipeline.

This script converts raw fetched GitHub issues into the smaller JSONL format
expected by rag/ingest.py.

Input:
    ml/data/raw/issues_raw_pandas_label_fetch.jsonl

Output:
    rag/data/resolved_issues.jsonl

The raw issue file currently contains issue bodies and metadata, but not the
actual comment text. The "comments" field is a count. Because of that, this
script prepares resolved issue problem chunks first. Maintainer answer comments
can be added later after a comments-fetching script is connected.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_INPUT_PATH = Path("ml/data/raw/issues_raw_pandas_label_fetch.jsonl")
DEFAULT_OUTPUT_PATH = Path("rag/data/resolved_issues.jsonl")

TARGET_LABEL_MAP = {
    "Bug": "bug",
    "Enhancement": "feature",
    "Docs": "docs",
    "Usage Question": "question",
}


def prepare_resolved_issues(
    *,
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> int:
    """Convert raw GitHub issues into RAG-ready resolved issue records."""

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_path}. "
            "Copy the raw pandas issues JSONL file into ml/data/raw/ first."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    written_count = 0

    with input_path.open("r", encoding="utf-8") as input_file, output_path.open(
        "w",
        encoding="utf-8",
    ) as output_file:
        for line_number, line in enumerate(input_file, start=1):
            line = line.strip()

            if not line:
                continue

            raw_issue = _parse_json_line(line, line_number)

            if not _is_closed_issue(raw_issue):
                continue

            mapped_labels = _map_issue_labels(raw_issue)

            if not mapped_labels:
                continue

            body = _clean_text(raw_issue.get("body"))

            if not body:
                continue

            rag_record = {
                "number": raw_issue["number"],
                "title": _clean_text(raw_issue.get("title")),
                "body": body,
                "labels": mapped_labels,
                "html_url": raw_issue.get("html_url"),
                "created_at": raw_issue.get("created_at"),
                "closed_at": raw_issue.get("closed_at"),
                "source_repo": "pandas-dev/pandas",
                "maintainer_comments": [],
                "notes": (
                    "Raw issue file contains a comment count but not comment text. "
                    "Maintainer comments should be added later after fetching comments."
                ),
            }

            output_file.write(json.dumps(rag_record, ensure_ascii=False) + "\n")
            written_count += 1

    return written_count


def _is_closed_issue(raw_issue: dict[str, Any]) -> bool:
    """Return True when the raw GitHub issue is closed."""

    return raw_issue.get("state") == "closed" and bool(raw_issue.get("closed_at"))


def _map_issue_labels(raw_issue: dict[str, Any]) -> list[str]:
    """Map GitHub labels to the four project labels."""

    labels = raw_issue.get("labels", [])
    mapped_labels: list[str] = []

    if not isinstance(labels, list):
        return mapped_labels

    for label in labels:
        if not isinstance(label, dict):
            continue

        label_name = label.get("name")

        if label_name in TARGET_LABEL_MAP:
            mapped_labels.append(TARGET_LABEL_MAP[label_name])

    return _deduplicate_preserve_order(mapped_labels)


def _clean_text(value: object) -> str:
    """Convert a raw value into clean text."""

    if not isinstance(value, str):
        return ""

    return " ".join(value.replace("\r\n", "\n").replace("\r", "\n").split()).strip()


def _parse_json_line(line: str, line_number: int) -> dict[str, Any]:
    """Parse one JSONL line with a helpful error message."""

    try:
        data = json.loads(line)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON on line {line_number}.") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object on line {line_number}.")

    return data


def _deduplicate_preserve_order(values: list[str]) -> list[str]:
    """Remove duplicate labels while preserving their original order."""

    seen: set[str] = set()
    result: list[str] = []

    for value in values:
        if value in seen:
            continue

        seen.add(value)
        result.append(value)

    return result


def main() -> None:
    """Prepare the default RAG resolved-issue corpus."""

    written_count = prepare_resolved_issues()
    print(f"Wrote {written_count} resolved issues to {DEFAULT_OUTPUT_PATH}")


if __name__ == "__main__":
    main()