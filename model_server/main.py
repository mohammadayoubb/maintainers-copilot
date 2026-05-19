
# “The model server is separate from the main API. The main API handles users, auth, chat, memory, and orchestration.
# The model server will later expose classifier, NER, and summarization endpoints.”
from fastapi import FastAPI

app = FastAPI(
    title="Maintainer's Copilot Model Server",
    version="0.1.0",
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "model-server"}