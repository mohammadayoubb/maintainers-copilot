"""Fetch GitHub issue comments for the RAG corpus.

The current RAG corpus contains issue title/body metadata, but not real
maintainer answer comments. This script enriches resolved issues by fetching
comments from the GitHub API.

Input:
    rag/data/resolved_issues.jsonl

Output:
    rag/data/resolved_issues_with_comments.jsonl

Why this matters:
The project requires RAG over project docs plus resolved issues with maintainer
answers. Issue bodies describe the problem, but maintainer comments often contain
the actual fix, explanation, or resolution.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_INPUT_PATH = Path("rag/data/resolved_issues.jsonl")
DEFAULT_OUTPUT_PATH = Path("rag/data/resolved_issues_with_comments.jsonl")

REPO_OWNER = "pandas-dev"
REPO_NAME = "pandas"

MAINTAINER_ASSOCIATIONS = {
    "OWNER",
    "MEMBER",
    "COLLABORATOR",
}


def fetch_comments_for_corpus(
    *,
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    max_issues: int | None = None,
    sleep_seconds: float = 0.2,
) -> int:
    """Fetch comments for resolved issues and write enriched JSONL records."""

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_path}. "
            "Run scripts/prepare_rag_corpus.py first."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    written_count = 0

    with input_path.open("r", encoding="utf-8") as input_file, output_path.open(
        "w",
        encoding="utf-8",
    ) as output_file:
        for line_number, line in enumerate(input_file, start=1):
            if max_issues is not None and written_count >= max_issues:
                break

            line = line.strip()

            if not line:
                continue

            issue = _parse_json_line(line, line_number)
            issue_number = int(issue["number"])

            comments = fetch_issue_comments(issue_number)
            maintainer_comments = extract_maintainer_comments(comments)

            enriched_issue = {
                **issue,
                "comments_fetched": len(comments),
                "maintainer_comments": maintainer_comments,
            }

            output_file.write(json.dumps(enriched_issue, ensure_ascii=False) + "\n")
            written_count += 1

            print(
                f"Fetched issue #{issue_number}: "
                f"{len(comments)} comments, "
                f"{len(maintainer_comments)} maintainer comments"
            )

            time.sleep(sleep_seconds)

    return written_count


def fetch_issue_comments(issue_number: int) -> list[dict[str, Any]]:
    """Fetch all GitHub comments for one issue."""

    all_comments: list[dict[str, Any]] = []
    page = 1

    while True:
        url = (
            f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
            f"/issues/{issue_number}/comments?per_page=100&page={page}"
        )

        comments = _github_get_json(url)

        if not isinstance(comments, list):
            raise RuntimeError(f"Unexpected GitHub response for issue #{issue_number}.")

        if not comments:
            break

        all_comments.extend(comments)

        if len(comments) < 100:
            break

        page += 1

    return all_comments


def extract_maintainer_comments(comments: list[dict[str, Any]]) -> list[str]:
    """Extract useful maintainer-like comments from GitHub comments."""

    maintainer_comments: list[str] = []

    for comment in comments:
        association = comment.get("author_association")

        if association not in MAINTAINER_ASSOCIATIONS:
            continue

        body = _clean_text(comment.get("body"))

        if not body:
            continue

        maintainer_comments.append(body)

    return maintainer_comments


def _github_get_json(url: str) -> Any:
    """Send a GET request to GitHub and return parsed JSON."""

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "maintainers-copilot-week7",
    }

    github_token = os.getenv("GITHUB_TOKEN")

    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    request = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)

    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"GitHub API request failed with status {exc.code}: {error_body}"
        ) from exc


def _clean_text(value: object) -> str:
    """Normalize comment/body text for storage."""

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


def main() -> None:
    """Fetch comments for the default resolved issue corpus."""

    max_issues_raw = os.getenv("MAX_ISSUES")
    max_issues = int(max_issues_raw) if max_issues_raw else None

    written_count = fetch_comments_for_corpus(max_issues=max_issues)
    print(f"Wrote {written_count} enriched issues to {DEFAULT_OUTPUT_PATH}")


if __name__ == "__main__":
    main()