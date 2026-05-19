"""Pydantic schemas for the model server.

This file defines the request and response models used by the ML/NLP
inference endpoints.

The model server will eventually expose:
- /classify for issue classification
- /ner for code-shaped entity extraction
- /summarize for issue thread summarization

Keeping schemas in one file makes the API contract clear and reusable.
"""

from typing import Literal

from pydantic import BaseModel, Field


IssueLabel = Literal["bug", "feature", "docs", "question"]


class ClassifyIssueRequest(BaseModel):
    """Request body for issue classification.

    The classifier receives the issue title and body, then predicts one of:
    bug, feature, docs, or question.
    """

    title: str = Field(..., min_length=1, description="GitHub issue title.")
    body: str | None = Field(default=None, description="GitHub issue body text.")


class ClassifyIssueResponse(BaseModel):
    """Response body returned by the classifier endpoint."""

    label: IssueLabel
    confidence: float = Field(..., ge=0.0, le=1.0)
    model: str


class Entity(BaseModel):
    """Single extracted code-shaped entity.

    Examples:
    - app.py as a file
    - JWTStrategy as a class
    - pandas as a package
    - ValueError as an error
    """

    text: str
    type: str


class NerRequest(BaseModel):
    """Request body for entity extraction."""

    text: str = Field(..., min_length=1)


class NerResponse(BaseModel):
    """Response body for entity extraction."""

    entities: list[Entity]


class SummarizeThreadRequest(BaseModel):
    """Request body for issue thread summarization.

    The summarizer receives the issue title, body, and optional comments.
    """

    title: str = Field(..., min_length=1)
    body: str | None = None
    comments: list[str] = Field(default_factory=list)


class SummarizeThreadResponse(BaseModel):
    """Response body for issue thread summarization."""

    summary: str
    resolution: str | None = None
    open_questions: list[str] = Field(default_factory=list)