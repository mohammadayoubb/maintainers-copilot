"""API exception handlers.

This file converts application/domain errors into HTTP responses.

Important architecture rule:
Services and repositories should not raise FastAPI HTTPException directly.
They raise domain errors instead.

Then this API boundary decides:
- which HTTP status code to return
- what safe message the user should see
- what error code should be included
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.domain.errors import (
    DomainError,
    NotFoundError,
    PermissionDeniedError,
    ToolFailureError,
    ValidationDomainError,
)
from app.infra.tracing import create_request_id


def status_code_for_error(error: DomainError) -> int:
    """Map a domain error to an HTTP status code.

    This function keeps the mapping in one place so the rest of the app
    does not need to know HTTP details.
    """
    if isinstance(error, NotFoundError):
        return 404

    if isinstance(error, PermissionDeniedError):
        return 403

    if isinstance(error, ValidationDomainError):
        return 400

    if isinstance(error, ToolFailureError):
        return 502

    return 500


async def domain_error_handler(request: Request, error: DomainError) -> JSONResponse:
    """Convert a DomainError into a structured JSON response.

    Users should never see Python stack traces.
    Instead, they receive:
    - stable error code
    - safe message
    - request ID for debugging
    """
    request_id = create_request_id()

    return JSONResponse(
        status_code=status_code_for_error(error),
        content={
            "error": {
                "code": error.code,
                "message": error.message,
                "request_id": request_id,
            }
        },
    )