"""Classification API routes.

This file exposes HTTP endpoints for issue classification.

Important architecture rule:
Routes should only handle HTTP concerns:
- receive request body
- call a service
- return a response

The route does not call the model server directly.
Instead, it calls ClassificationService, which then calls the model-server
HTTP client in app/infra/model_client.py.
"""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.services.classification_service import (
    ClassificationService,
    get_classification_service,
)

# All routes in this file are grouped under /classification.
router = APIRouter(prefix="/classification", tags=["classification"])


class ClassificationRequest(BaseModel):
    """Request body for classifying a GitHub issue."""

    title: str = Field(..., min_length=1, description="GitHub issue title.")
    body: str | None = Field(default=None, description="GitHub issue body.")


class ClassificationResponse(BaseModel):
    """Response body returned by the classification API route."""

    label: str
    confidence: float
    model: str


@router.post("/classify", response_model=ClassificationResponse)
async def classify_issue_endpoint(
    request: ClassificationRequest,
    service: ClassificationService = Depends(get_classification_service),
) -> dict[str, Any]:
    """Classify a GitHub issue using the model server.

    This endpoint is part of the main API.

    The route itself does not know how the model works.
    It delegates classification to the service layer.
    """
    return service.classify_issue(
        title=request.title,
        body=request.body,
    )