"""Production-shaped model server entrypoint.

This file is reserved for the real classifier/NER/summarizer server.

For local Docker integration, the project uses model_server/main_dev.py
through Dockerfile.model-server. The dev server keeps the same HTTP contract
without loading heavy PyTorch artifacts.

Before production deployment, this file should load:
- the fine-tuned DistilBERT issue classifier
- the code-shaped entity extractor
- the summarization implementation
"""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="Maintainer Copilot Model Server")


@app.get("/")
def health() -> dict[str, str]:
    """Return a health message explaining this entrypoint."""

    return {
        "status": "not_configured",
        "service": "model-server",
        "message": "Use model_server.main_dev for local Docker smoke tests, or restore the real model loader here.",
    }