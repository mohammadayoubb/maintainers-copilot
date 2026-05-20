"""Model server FastAPI application.

The model server is responsible for ML/NLP inference endpoints.

It exposes:
- /health for service health checks
- /classify for issue classification
- /ner for code-shaped entity extraction
- /summarize for issue thread summarization

Keeping this service separate from the main API makes the architecture cleaner:
the main API handles users, auth, chat, memory, and orchestration,
while the model server handles ML/NLP inference.
"""

from fastapi import FastAPI

from model_server.classifier import classify_issue
from model_server.ner import extract_entities
from model_server.schemas import (
    ClassifyIssueRequest,
    ClassifyIssueResponse,
    NerRequest,
    NerResponse,
    SummarizeThreadRequest,
    SummarizeThreadResponse,
)
from model_server.summarizer import summarize_thread

# Create a separate FastAPI app for model inference.
app = FastAPI(
    title="Maintainer's Copilot Model Server",
    version="0.1.0",
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Return a simple status response for the model server.

    This confirms that the model-server service is running.
    Later, the main API can use this endpoint to check whether
    ML inference is available.
    """
    return {
        "status": "ok",
        "service": "model-server",
    }


@app.post("/classify", response_model=ClassifyIssueResponse)
async def classify_endpoint(request: ClassifyIssueRequest) -> ClassifyIssueResponse:
    """Classify a GitHub issue.

    This endpoint wraps the classifier function so other services can call
    classification through HTTP.
    """
    return classify_issue(request)


@app.post("/ner", response_model=NerResponse)
async def ner_endpoint(request: NerRequest) -> NerResponse:
    """Extract code-shaped entities from issue text.

    This endpoint is used as a chatbot tool later.
    """
    return extract_entities(request)


@app.post("/summarize", response_model=SummarizeThreadResponse)
async def summarize_endpoint(request: SummarizeThreadRequest) -> SummarizeThreadResponse:
    """Summarize an issue thread.

    This endpoint is used as a chatbot tool later.
    """
    return summarize_thread(request)