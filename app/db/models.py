"""SQLAlchemy ORM models.

This file defines the database tables used by the application.

Important architecture rule:
ORM models are for persistence only.
Routes should not use these models directly.

Later flow:
API route -> Service -> Repository -> ORM model -> Database

For Day 1, we start with the issues table because the project depends
on fetched GitHub issues for classification, RAG, and evaluation.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models.

    Alembic will later use this metadata to detect tables and generate
    database migrations.
    """

    pass


class Issue(Base):
    """GitHub issue stored in the local database.

    This table stores fetched closed issues from the chosen open-source repo.

    It supports:
    - ML classification training
    - train/validation/test split tracking
    - RAG corpus building from resolved issues
    """

    __tablename__ = "issues"

    # Internal database primary key.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # GitHub issue number/id from the source repository.
    github_issue_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)

    # Repository name, for example: fastapi/fastapi.
    repo_name: Mapped[str] = mapped_column(String(255), index=True)

    # GitHub issue title.
    title: Mapped[str] = mapped_column(String(500))

    # GitHub issue body. Text is used because bodies can be long.
    body: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Original GitHub labels stored as JSON.
    labels: Mapped[list[str]] = mapped_column(JSONB)

    # Mapped project label: bug, feature, docs, or question.
    mapped_label: Mapped[str | None] = mapped_column(String(50), index=True)

    # GitHub issue state. For this project, we mainly fetch closed issues.
    state: Mapped[str] = mapped_column(String(50), default="closed")

    # Dataset split: train, val, test, or rag_holdout.
    split: Mapped[str | None] = mapped_column(String(50), index=True)

    # Original GitHub issue URL.
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # When the issue was created on GitHub.
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # When the issue was closed on GitHub.
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Local timestamp for when this row was inserted.
    inserted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class IssueComment(Base):
    """Comment belonging to a GitHub issue.

    Comments are useful later for:
    - summarization
    - RAG resolved issue corpus
    - finding maintainer answers
    """

    __tablename__ = "issue_comments"

    # Internal database primary key.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # The local Issue.id this comment belongs to.
    issue_id: Mapped[int] = mapped_column(Integer, index=True)

    # GitHub username of the comment author.
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # GitHub author association, for example MEMBER, OWNER, CONTRIBUTOR, NONE.
    author_association: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Comment body text.
    body: Mapped[str] = mapped_column(Text)

    # Original GitHub comment metadata.
    comment_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # When the comment was created on GitHub.
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Local timestamp for when this row was inserted.
    inserted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )