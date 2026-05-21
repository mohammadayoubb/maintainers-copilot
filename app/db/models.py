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

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
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

class User(Base):
    """Application user.

    This table is intentionally compatible with fastapi-users style fields.

    The role field supports the project requirement:
    - user: normal chatbot user
    - admin: can configure widgets and manage admin-only features
    """

    __tablename__ = "users"

    # Internal application user ID.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # User email used for login.
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)

    # Lowercased/normalized email used by auth systems for lookups.
    normalized_email: Mapped[str] = mapped_column(String(320), unique=True, index=True)

    # Hashed password, never the plain password.
    hashed_password: Mapped[str] = mapped_column(String(1024))

    # fastapi-users compatible account status fields.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Project-level role used by our authorization checks.
    role: Mapped[str] = mapped_column(String(50), default="user", index=True)

    # Local timestamp for when the user was created.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class Conversation(Base):
    """Chat conversation owned by a user.

    Conversations let the chatbot group messages together and support
    later memory inspection or deletion.
    """

    __tablename__ = "conversations"

    # Internal conversation ID.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # User who owns this conversation.
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    # Optional widget public ID if the conversation started from an embedded widget.
    widget_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Human-readable conversation title.
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Soft deletion timestamp.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Creation timestamp.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Last update timestamp.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class Message(Base):
    """Single chat message inside a conversation.

    Content is stored after redaction so secrets are not persisted.
    """

    __tablename__ = "messages"

    # Internal message ID.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Conversation this message belongs to.
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)

    # Message role: user, assistant, tool, or system.
    role: Mapped[str] = mapped_column(String(50), index=True)

    # Redacted message content.
    content_redacted: Mapped[str] = mapped_column(Text)

    # Trace ID used to connect this message to observability traces.
    trace_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Message creation timestamp.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class Memory(Base):
    """Long-term chatbot memory.

    The project requires long-term memory in Postgres with pgvector.
    For this batch, we create the metadata/content table first.
    The vector column can be added later after confirming the pgvector
    SQLAlchemy dependency and migration setup.
    """

    __tablename__ = "memories"

    # Internal memory ID.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # User this memory belongs to.
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    # Memory type: semantic, episodic, or procedural.
    memory_type: Mapped[str] = mapped_column(String(50), default="semantic", index=True)

    # Redacted memory content.
    content: Mapped[str] = mapped_column(Text)

    # Optional source conversation.
    source_conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversations.id"),
        nullable=True,
        index=True,
    )

    # Extra metadata such as tool name or source message ID.
    memory_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Creation timestamp.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Last update timestamp.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class WidgetConfig(Base):
    """Embeddable widget configuration.

    Admins create these configs later from the Streamlit admin page.
    The public_widget_id is what the host page uses in the script tag.
    """

    __tablename__ = "widget_configs"

    # Internal widget config ID.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Public ID used by the embed script.
    public_widget_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    # Allowed origins list, stored as JSON.
    allowed_origins: Mapped[list[str]] = mapped_column(JSONB)

    # Theme config such as primary color and position.
    theme: Mapped[dict[str, Any]] = mapped_column(JSONB)

    # Greeting shown when widget opens.
    greeting: Mapped[str] = mapped_column(String(500), default="How can I help?")

    # Enabled tool names for this widget.
    enabled_tools: Mapped[list[str]] = mapped_column(JSONB)

    # Whether the widget config is active.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Admin user who created this config.
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    # Creation timestamp.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Last update timestamp.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class AuditLog(Base):
    """Audit log for security-sensitive actions.

    Required project actions include:
    - role changes
    - memory writes
    - widget config changes
    - conversation deletions
    """

    __tablename__ = "audit_logs"

    # Internal audit log ID.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # User who performed the action.
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    # Action name, for example memory_write or widget_config_update.
    action: Mapped[str] = mapped_column(String(255), index=True)

    # Target type, for example memory, widget_config, conversation, or user.
    target_type: Mapped[str] = mapped_column(String(100), index=True)

    # Target ID as text so it can support integer IDs and public widget IDs.
    target_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Redacted metadata about the action.
    audit_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Audit timestamp.
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )