"""Domain-level error types.

This file defines application/business errors.

Important architecture rule:
Domain errors should not depend on FastAPI.
That means we do NOT raise HTTPException from services or repositories.

Instead:
- services raise these domain errors
- API exception handlers convert them into HTTP responses

This keeps the business logic independent from the web framework.
"""


class DomainError(Exception):
    """Base class for all application-specific errors.

    Every custom error should inherit from this class so the API layer
    can catch application errors in one place.
    """

    code = "DOMAIN_ERROR"
    message = "An application error occurred."

    def __init__(self, message: str | None = None) -> None:
        """Create a domain error with an optional custom message."""
        self.message = message or self.message
        super().__init__(self.message)


class NotFoundError(DomainError):
    """Raised when a requested resource does not exist."""

    code = "NOT_FOUND"
    message = "The requested resource was not found."


class PermissionDeniedError(DomainError):
    """Raised when a user does not have permission for an action."""

    code = "PERMISSION_DENIED"
    message = "You do not have permission to perform this action."


class ToolFailureError(DomainError):
    """Raised when an external tool or model call fails.

    Example:
    - classifier service is down
    - summarizer service times out
    - RAG pipeline fails
    """

    code = "TOOL_FAILURE"
    message = "A tool failed while processing the request."


class ValidationDomainError(DomainError):
    """Raised when business-level validation fails.

    This is different from Pydantic request validation.
    Example:
    A widget config is syntactically valid JSON, but the allowed origins
    list is empty when the business rule requires at least one origin.
    """

    code = "VALIDATION_ERROR"
    message = "The request failed business validation."