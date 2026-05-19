"""Redaction infrastructure module.

This file removes sensitive values before text is written to:
- logs
- traces
- memory
- retrieved chunk snapshots

The goal is to prevent secrets from leaking if a user pastes sensitive
content into the chatbot, such as API keys, GitHub tokens, JWTs,
passwords, or database URLs.

Important architecture rule:
Redaction belongs in app/infra because it protects data before it leaves
the service boundary.
"""

import re

# Replacement text used whenever a sensitive value is detected.
REDACTED = "[REDACTED]"


# Each pattern detects one type of sensitive data.
# Later, we can extend this list as we discover more risky patterns.
SENSITIVE_PATTERNS: list[re.Pattern[str]] = [
    # OpenAI-style API keys, usually starting with sk-.
    re.compile(r"sk-[A-Za-z0-9_\-]{10,}"),

    # GitHub classic personal access tokens.
    re.compile(r"ghp_[A-Za-z0-9_]{10,}"),

    # GitHub fine-grained personal access tokens.
    re.compile(r"github_pat_[A-Za-z0-9_]{10,}"),

    # Bearer tokens in authorization headers.
    re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]+", re.IGNORECASE),

    # Simple password assignments such as password=abc123.
    re.compile(r"password\s*=\s*[^,\s]+", re.IGNORECASE),

    # Database URLs that may contain usernames and passwords.
    re.compile(r"postgresql(?:\+\w+)?://[^\s]+", re.IGNORECASE),
]


def redact_text(text: str) -> str:
    """Return text with sensitive patterns replaced.

    This function is intentionally small and reusable.
    Any service that is about to log, trace, or store user-provided text
    should call this function first.
    """
    redacted = text

    for pattern in SENSITIVE_PATTERNS:
        redacted = pattern.sub(REDACTED, redacted)

    return redacted


def redact_dict(data: dict[str, object]) -> dict[str, object]:
    """Return a copy of a dictionary with string values redacted.

    This is useful for structured logs and trace attributes where data
    is often stored as key-value pairs.
    """
    redacted_data: dict[str, object] = {}

    for key, value in data.items():
        if isinstance(value, str):
            redacted_data[key] = redact_text(value)
        else:
            redacted_data[key] = value

    return redacted_data