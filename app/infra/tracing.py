"""Tracing infrastructure module.

This file provides small tracing helpers for the foundation stage.

In the final project, tracing should show what happened during a request:
- user message received
- LLM call started
- tool call started
- classifier call started
- RAG retrieval started
- reranking started
- memory write started

For now, this file creates simple trace/request IDs that we can attach
to logs and responses. Later, this can be replaced or extended with a
real tracing backend such as OpenTelemetry, Jaeger, Langfuse, or Phoenix.
"""

from uuid import uuid4


def create_request_id() -> str:
    """Create a unique request ID.

    A request ID identifies one API request.

    Example:
    If a user sends one chat message, that HTTP request gets one request ID.
    If an error happens, the frontend can show this request ID and the logs
    can use the same ID to find what happened.
    """
    return f"req_{uuid4().hex}"


def create_trace_id() -> str:
    """Create a unique trace ID.

    A trace ID identifies the full flow of one operation.

    Example:
    One chatbot message may include:
    - API receives message
    - LLM chooses a tool
    - classifier tool runs
    - RAG tool runs
    - final answer is generated

    All of that should share one trace ID.
    """
    return f"trace_{uuid4().hex}"


def create_span_id() -> str:
    """Create a unique span ID.

    A span is one step inside a trace.

    Example spans:
    - classifier_call
    - rag_dense_search
    - rag_rerank
    - llm_generation
    """
    return f"span_{uuid4().hex}"