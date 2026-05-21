"""Tests for API exception handling.

These tests make sure domain errors are converted into safe HTTP-style JSON
responses at the API boundary.

The goal is to prove that users receive structured errors instead of Python
stack traces.
"""

import asyncio

from fastapi import Request

from app.api.exception_handlers import domain_error_handler, status_code_for_error
from app.domain.errors import (
    NotFoundError,
    PermissionDeniedError,
    ToolFailureError,
    ValidationDomainError,
)


def test_status_code_for_domain_errors() -> None:
    """Domain errors should map to the expected HTTP status codes."""

    assert status_code_for_error(NotFoundError("Missing resource.")) == 404
    assert status_code_for_error(PermissionDeniedError("Access denied.")) == 403
    assert status_code_for_error(ValidationDomainError("Invalid input.")) == 400
    assert status_code_for_error(ToolFailureError("Tool failed.")) == 502


def make_fake_request() -> Request:
    """Create a minimal fake FastAPI request for handler testing."""

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "headers": [],
    }

    return Request(scope)


def test_domain_error_handler_returns_structured_error() -> None:
    """The handler should return safe structured JSON without stack traces."""

    request = make_fake_request()
    error = ToolFailureError("RAG retrieval failed.")

    response = asyncio.run(domain_error_handler(request, error))

    assert response.status_code == 502

    body = response.body.decode("utf-8")

    assert "TOOL_FAILURE" in body
    assert "RAG retrieval failed." in body
    assert "request_id" in body
    assert "Traceback" not in body
