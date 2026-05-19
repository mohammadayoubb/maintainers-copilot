"""HTTP client for the model server.

This file owns communication between the main API and the model server.

Important architecture rule:
The main API should not import model_server.classifier directly.
Instead, it should call the model server over HTTP.

This keeps ML/NLP inference separate from API orchestration.

The model server exposes:
- POST /classify
- POST /ner
- POST /summarize
"""

import json
from typing import Any
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

from app.domain.errors import ToolFailureError


MODEL_SERVER_URL = "http://model-server:8001"


def _post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Send a JSON POST request to the model server.

    Args:
        path: Endpoint path such as /classify.
        payload: JSON body sent to the model server.

    Returns:
        Parsed JSON response from the model server.

    Raises:
        ToolFailureError: If the model server is unreachable or returns an error.
    """
    url = f"{MODEL_SERVER_URL}{path}"

    encoded_payload = json.dumps(payload).encode("utf-8")

    request = urllib_request.Request(
        url=url,
        data=encoded_payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib_request.urlopen(request, timeout=10) as response:
            response_body = response.read().decode("utf-8")
            return dict(json.loads(response_body))

    except HTTPError as exc:
        raise ToolFailureError(
            f"Model server returned HTTP {exc.code} while calling {path}."
        ) from exc

    except URLError as exc:
        raise ToolFailureError(
            f"Model server is unreachable while calling {path}."
        ) from exc

    except TimeoutError as exc:
        raise ToolFailureError(
            f"Model server timed out while calling {path}."
        ) from exc


def classify_issue(title: str, body: str | None = None) -> dict[str, Any]:
    """Call the model server /classify endpoint."""
    return _post_json(
        "/classify",
        {
            "title": title,
            "body": body,
        },
    )


def extract_entities(text: str) -> dict[str, Any]:
    """Call the model server /ner endpoint."""
    return _post_json(
        "/ner",
        {
            "text": text,
        },
    )


def summarize_thread(
    title: str,
    body: str | None = None,
    comments: list[str] | None = None,
) -> dict[str, Any]:
    """Call the model server /summarize endpoint."""
    return _post_json(
        "/summarize",
        {
            "title": title,
            "body": body,
            "comments": comments or [],
        },
    )