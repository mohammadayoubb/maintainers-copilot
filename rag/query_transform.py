"""Query transformation utilities for the Maintainer's Copilot RAG pipeline.

Day 3 requires at least one query transformation technique.

This first version uses deterministic keyword expansion. It is simple, testable,
and useful for GitHub issue questions because users often ask short questions
like "csv broken" while the docs/issues may contain more specific terms like
"read_csv", "parser", "DataFrame", or "ValueError".

Later, this can be upgraded to an LLM rewrite while keeping the same function
interface.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class QueryTransformResult:
    """Result of transforming a user query before retrieval."""

    original_query: str
    rewritten_query: str
    added_terms: list[str]


DOMAIN_EXPANSIONS: dict[str, list[str]] = {
    "csv": ["read_csv", "parser", "DataFrame", "delimiter"],
    "excel": ["read_excel", "xlsx", "openpyxl", "sheet_name"],
    "json": ["read_json", "json_normalize", "orient"],
    "groupby": ["aggregation", "agg", "transform", "apply"],
    "merge": ["join", "concat", "keys", "DataFrame.merge"],
    "date": ["datetime", "to_datetime", "Timestamp", "timezone"],
    "install": ["pip", "conda", "dependency", "version"],
    "performance": ["slow", "memory", "optimization", "vectorized"],
    "warning": ["FutureWarning", "DeprecationWarning", "UserWarning"],
    "error": ["exception", "traceback", "ValueError", "TypeError"],
    "bug": ["regression", "unexpected behavior", "reproduce"],
    "docs": ["documentation", "example", "guide"],
}


def transform_query(query: str) -> QueryTransformResult:
    """Rewrite a maintainer question into a retrieval-friendly query.

    The function keeps the user's original words and adds domain terms that are
    likely to appear in pandas docs or resolved issues.
    """

    cleaned_query = normalize_query(query)
    added_terms = find_expansion_terms(cleaned_query)

    if added_terms:
        rewritten_query = f"{cleaned_query} {' '.join(added_terms)}"
    else:
        rewritten_query = cleaned_query

    return QueryTransformResult(
        original_query=query,
        rewritten_query=rewritten_query,
        added_terms=added_terms,
    )


def normalize_query(query: str) -> str:
    """Normalize query spacing while preserving code-shaped terms."""

    query = query.strip()
    query = re.sub(r"\s+", " ", query)
    return query


def find_expansion_terms(query: str) -> list[str]:
    """Find domain-specific expansion terms for the query."""

    query_tokens = set(re.findall(r"[a-zA-Z0-9_./:-]+", query.lower()))
    added_terms: list[str] = []

    for trigger, expansions in DOMAIN_EXPANSIONS.items():
        if trigger in query_tokens:
            added_terms.extend(expansions)

    return deduplicate_preserve_order(added_terms)


def deduplicate_preserve_order(values: list[str]) -> list[str]:
    """Remove duplicates without changing the original order."""

    seen: set[str] = set()
    result: list[str] = []

    for value in values:
        key = value.lower()

        if key in seen:
            continue

        seen.add(key)
        result.append(value)

    return result