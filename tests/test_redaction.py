"""Tests for the redaction infrastructure.

The project requires sensitive values to be removed before text is written to:
- logs
- traces
- memory
- retrieved chunk snapshots

These tests make sure fake secrets do not survive redaction.
"""

from app.infra.redaction import REDACTED, redact_dict, redact_text


def test_redact_text_removes_openai_api_key() -> None:
    """OpenAI-style keys should never appear unredacted."""

    raw_text = "User pasted this key: sk-test1234567890abcdef"
    redacted = redact_text(raw_text)

    assert "sk-test1234567890abcdef" not in redacted
    assert REDACTED in redacted


def test_redact_text_removes_github_tokens() -> None:
    """GitHub personal access tokens should be redacted."""

    raw_text = (
        "Classic token: ghp_abcdefghijklmnopqrstuvwxyz123456 "
        "Fine-grained token: github_pat_abcdefghijklmnopqrstuvwxyz123456"
    )

    redacted = redact_text(raw_text)

    assert "ghp_abcdefghijklmnopqrstuvwxyz123456" not in redacted
    assert "github_pat_abcdefghijklmnopqrstuvwxyz123456" not in redacted
    assert redacted.count(REDACTED) == 2


def test_redact_text_removes_bearer_token() -> None:
    """Authorization bearer tokens should be redacted."""

    raw_text = "Authorization: Bearer abc.def.ghi"
    redacted = redact_text(raw_text)

    assert "Bearer abc.def.ghi" not in redacted
    assert REDACTED in redacted


def test_redact_text_removes_password_assignment() -> None:
    """Simple password assignments should be redacted."""

    raw_text = "database password=my-secret-password should not be logged"
    redacted = redact_text(raw_text)

    assert "password=my-secret-password" not in redacted
    assert REDACTED in redacted


def test_redact_text_removes_database_url() -> None:
    """Database URLs with credentials should be redacted."""

    raw_text = "postgresql://user:secret-password@localhost:5432/app"
    redacted = redact_text(raw_text)

    assert "secret-password" not in redacted
    assert REDACTED in redacted


def test_redact_dict_redacts_string_values() -> None:
    """Structured log dictionaries should redact string values."""

    raw_data = {
        "message": "token sk-test1234567890abcdef",
        "count": 3,
        "enabled": True,
    }

    redacted = redact_dict(raw_data)

    assert "sk-test1234567890abcdef" not in str(redacted["message"])
    assert redacted["count"] == 3
    assert redacted["enabled"] is True