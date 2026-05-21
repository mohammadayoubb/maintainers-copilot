"""Lightweight model server for local Day 4 chatbot tool testing.

This keeps the same HTTP contract as the real model server:
- POST /classify
- POST /ner
- POST /summarize

It avoids PyTorch so the Docker build stays small and fast.
"""

from __future__ import annotations

import re
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Maintainer Copilot Model Server")


class ClassifyRequest(BaseModel):
    """Request body for issue classification."""

    title: str
    body: str | None = None


class NerRequest(BaseModel):
    """Request body for entity extraction."""

    text: str


class SummarizeRequest(BaseModel):
    """Request body for thread summarization."""

    title: str
    body: str | None = None
    comments: list[str] | None = None


@app.get("/")
def health() -> dict[str, str]:
    """Basic health check."""
    return {"status": "ok", "service": "model-server-dev"}


@app.post("/classify")
def classify(request: ClassifyRequest) -> dict[str, Any]:
    """Classify an issue using simple rules for local integration testing."""
    text = f"{request.title} {request.body or ''}".lower()

    if any(
        word in text
        for word in ["bug", "error", "fails", "failure", "exception", "traceback"]
    ):
        label = "bug"
        confidence = 0.75
    elif any(
        word in text
        for word in ["feature", "enhancement", "support add", "request"]
    ):
        label = "feature"
        confidence = 0.70
    elif any(word in text for word in ["docs", "documentation", "readme", "guide"]):
        label = "docs"
        confidence = 0.70
    else:
        label = "question"
        confidence = 0.65

    return {
        "label": label,
        "confidence": confidence,
        "model": "dev-rule-based-classifier",
    }


@app.post("/ner")
def ner(request: NerRequest) -> dict[str, Any]:
    """Extract simple code-shaped entities."""
    text = request.text
    entities: list[dict[str, str]] = []

    for match in re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\(\)?", text):
        entities.append({"text": match, "type": "function_or_identifier"})

    for match in re.findall(r"\b[\w\-]+\.(?:py|csv|json|md|txt|yml|yaml)\b", text):
        entities.append({"text": match, "type": "file"})

    for match in re.findall(r"\b[A-Z][A-Za-z]+Error\b", text):
        entities.append({"text": match, "type": "error"})

    return {"entities": entities}


@app.post("/summarize")
def summarize(request: SummarizeRequest) -> dict[str, Any]:
    """Return a lightweight summary for local integration testing."""
    body = request.body or ""
    comments = request.comments or []

    return {
        "summary": f"{request.title}. {body[:180]}",
        "resolution": "No final resolution detected in dev summarizer.",
        "open_questions": [] if comments else ["No comments were provided."],
    }