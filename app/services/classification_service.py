"""Classification service.

This file contains business-level classification logic for the main API.

Important architecture rule:
Routes should not call the model server directly.
Routes should call services, and services coordinate infrastructure clients.

Flow:
API route
  -> ClassificationService
  -> app.infra.model_client
  -> model-server /classify
"""

from typing import Any

from app.infra import model_client


class ClassificationService:
    """Service responsible for issue classification use cases.

    For now, this service simply calls the model-server HTTP client.

    Later, this service can also:
    - record latency
    - add tracing spans
    - redact logs
    - choose fallback behavior if the model server is unavailable
    - store classification results
    """

    def classify_issue(self, title: str, body: str | None = None) -> dict[str, Any]:
        """Classify a GitHub issue using the model server.

        Args:
            title: GitHub issue title.
            body: Optional GitHub issue body.

        Returns:
            A dictionary containing label, confidence, and model name.
        """
        return model_client.classify_issue(title=title, body=body)


def get_classification_service() -> ClassificationService:
    """Create a classification service instance.

    Later, this function can be used as a FastAPI dependency.
    """
    return ClassificationService()