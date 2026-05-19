"""Code-shaped entity extraction for the model server.

This file owns the NER-style extraction logic used by the /ner endpoint.

The goal is not to train a full NER model from scratch.
The project asks for an NER tool that extracts code-shaped entities from
issue text, such as:
- file names
- class names
- function names
- package names
- error names
- version numbers
- environment variables
- URLs

For the first working version, we use regex/rule-based extraction.
This is fast, explainable, and good enough for integration.
"""

import re

from model_server.schemas import Entity, NerRequest, NerResponse


# File names like app.py, config.toml, package.json, README.md.
FILE_PATTERN = re.compile(r"\b[\w\-\/]+\.(?:py|js|ts|tsx|json|toml|yaml|yml|md|txt|csv)\b")

# Python-style class names like DataFrame, JWTStrategy, UserManager.
CLASS_PATTERN = re.compile(r"\b[A-Z][a-zA-Z0-9]+(?:[A-Z][a-zA-Z0-9]+)+\b")

# Function-like names followed by parentheses, such as read_csv().
FUNCTION_PATTERN = re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*\(\)")

# Common error/exception names like ValueError, TypeError, ImportError.
ERROR_PATTERN = re.compile(r"\b[A-Z][a-zA-Z]+(?:Error|Exception)\b")

# Version strings like 1.2.3, v2.0.1, Python 3.11.
VERSION_PATTERN = re.compile(r"\b(?:v)?\d+\.\d+(?:\.\d+)?\b")

# Environment variables like DATABASE_URL, OPENAI_API_KEY, VAULT_TOKEN.
ENV_VAR_PATTERN = re.compile(r"\b[A-Z][A-Z0-9_]{2,}\b")

# URLs from issue text.
URL_PATTERN = re.compile(r"https?://[^\s]+")


def _add_matches(entities: list[Entity], text: str, pattern: re.Pattern[str], entity_type: str) -> None:
    """Find pattern matches and append them as entities.

    Args:
        entities: The list we are collecting extracted entities into.
        text: The issue text to search.
        pattern: Regex pattern used to find entities.
        entity_type: Label describing the entity type.
    """
    for match in pattern.finditer(text):
        entities.append(
            Entity(
                text=match.group(0),
                type=entity_type,
            )
        )


def deduplicate_entities(entities: list[Entity]) -> list[Entity]:
    """Remove duplicate entities while preserving order.

    The same entity can be matched by multiple rules or appear multiple
    times in the issue text. This keeps the response clean.
    """
    seen: set[tuple[str, str]] = set()
    unique_entities: list[Entity] = []

    for entity in entities:
        key = (entity.text, entity.type)

        if key in seen:
            continue

        seen.add(key)
        unique_entities.append(entity)

    return unique_entities


def extract_entities(request: NerRequest) -> NerResponse:
    """Extract code-shaped entities from issue text.

    This function is called by the /ner endpoint.
    """
    text = request.text
    entities: list[Entity] = []

    _add_matches(entities, text, FILE_PATTERN, "file")
    _add_matches(entities, text, CLASS_PATTERN, "class")
    _add_matches(entities, text, FUNCTION_PATTERN, "function")
    _add_matches(entities, text, ERROR_PATTERN, "error")
    _add_matches(entities, text, VERSION_PATTERN, "version")
    _add_matches(entities, text, ENV_VAR_PATTERN, "environment_variable")
    _add_matches(entities, text, URL_PATTERN, "url")

    return NerResponse(entities=deduplicate_entities(entities))