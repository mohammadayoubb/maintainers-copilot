# Maintainer's Copilot Architecture

## 1. Project Overview

Maintainer's Copilot is an authenticated assistant for open-source maintainers. It helps triage GitHub issues by:

- classifying issues into `bug`, `feature`, `docs`, or `question`
- extracting code-shaped entities
- summarizing issue threads
- retrieving relevant context from resolved issues using RAG
- storing explicit long-term memory
- storing short-term conversation state in Redis
- exposing the assistant through Streamlit and an embeddable widget

The selected dataset/repository is:

```text
pandas-dev/pandas
```

## 2. High-Level System

```text
User / Maintainer
   |
   | uses
   v
Streamlit UI OR Embedded Widget
   |
   | HTTP
   v
FastAPI API
   |
   | calls services
   v
app/services/
   |
   | uses repositories and infra adapters
   v
Postgres / Redis / Vault / Model Server / RAG files
```

## 3. Docker Services

The local stack uses these services:

| Service | Purpose |
|---|---|
| `api` | FastAPI backend for auth, chat, tools, memory, widget loader |
| `model-server` | ML/NLP inference endpoints: classify, NER, summarize |
| `chatbot` | Streamlit internal UI |
| `widget` | Static server for embedded widget UI |
| `host` | Demo host page that embeds the widget |
| `migrate` | Runs Alembic migrations |
| `db` | Postgres database with pgvector image |
| `redis` | Short-term memory and temporary conversation state |
| `minio` | Local S3-compatible blob storage |
| `vault` | Local dev secret manager |

## 4. Application Layers

The codebase follows a layered architecture.

### `app/api/`

API routes only handle HTTP concerns.

Responsibilities:

- receive request bodies
- call dependency functions
- call services
- return response models

API routes should not directly query SQL, call Redis, call Vault, or call model providers.

### `app/services/`

Services own business logic.

Responsibilities:

- coordinate repositories
- coordinate infrastructure adapters
- enforce business rules
- manage memory write flow
- route chatbot tool calls

Example:

```text
Chat route -> ChatService -> model client / RAG service / memory service
```

### `app/repositories/`

Repositories own SQL access.

Responsibilities:

- insert rows
- query rows
- update rows
- delete rows

Repositories should not raise FastAPI HTTP exceptions and should not call external services.

### `app/domain/`

Domain contains business models and domain errors.

Examples:

- `NotFoundError`
- `PermissionDeniedError`
- `ValidationDomainError`
- `ToolFailureError`

### `app/infra/`

Infra contains external adapters.

Examples:

- Vault
- Redis
- model server client
- redaction
- startup checks

## 5. Authentication Flow

Authentication uses `fastapi-users` with JWT.

```text
User submits email/password
   |
   v
POST /auth/jwt/login
   |
   v
FastAPI verifies user credentials
   |
   v
JWT access token returned
   |
   v
Client sends Authorization: Bearer <token>
```

The JWT signing key is loaded from Vault during API startup.

## 6. Chat Flow

```text
POST /chat
   |
   v
Chat route receives message and current user
   |
   v
ChatService checks conversation ownership
   |
   v
Message is redacted and saved to Postgres
   |
   v
Message is saved to Redis short-term memory
   |
   v
ChatService routes message to a tool
   |
   v
Assistant response is formatted
   |
   v
Assistant response is redacted, saved to Postgres, and saved to Redis
```

The deterministic router currently supports:

- `classify_issue`
- `extract_entities`
- `summarize_thread`
- `rag_answer`
- `write_memory`

A future improvement is replacing the deterministic router with one tool-calling LLM while keeping the same underlying tools.

## 7. Tool Flow

### Classification

```text
ChatService
   |
   v
app.infra.model_client.classify_issue()
   |
   v
model-server POST /classify
```

### NER

```text
ChatService
   |
   v
app.infra.model_client.extract_entities()
   |
   v
model-server POST /ner
```

### Summarization

```text
ChatService
   |
   v
app.infra.model_client.summarize_thread()
   |
   v
model-server POST /summarize
```

### RAG

```text
ChatService
   |
   v
RagService.retrieve_context()
   |
   v
local RAG pipeline
   |
   v
retrieved grounding chunks
```

## 8. RAG Architecture

The evaluated RAG pipeline uses:

- structure-aware chunking
- BAAI/bge-small-en embeddings
- hybrid dense + sparse retrieval
- dense weight: `0.8`
- sparse weight: `0.2`
- reranking
- deterministic query transformation
- metadata filtering support

The best Day 3 retrieval result was:

```text
hit@5 = 1.0000
MRR@10 ≈ 0.7307
```

The API also includes a lightweight sparse fallback when local embedding dependencies are unavailable. This fallback is for graceful degradation and local integration; it does not replace the evaluated RAG pipeline.

## 9. Memory Architecture

### Short-Term Memory

Short-term memory is stored in Redis.

Key format:

```text
chat:conversation:{conversation_id}:messages
```

TTL:

```text
1800 seconds = 30 minutes
```

This is long enough for normal chat pauses and short enough to avoid keeping temporary conversation state forever.

### Long-Term Memory

Long-term memory is stored in Postgres.

Current memory type:

```text
semantic
```

Writes are explicit only. The chatbot does not silently write long-term memory.

Example:

```text
Remember that this user prefers concise maintainer answers.
```

Each long-term memory write creates an audit log row.

## 10. Frontends

### Streamlit

Streamlit is the internal/admin interface.

It supports:

- login
- register
- JWT session state
- chat
- quick prompts
- conversation continuation

### Embedded Widget

The widget is embedded through one script tag:

```html
<script src="http://localhost:8000/widget.js" data-widget-id="demo-widget"></script>
```

The loader injects an iframe that points to the widget UI.

Current widget features:

- collapsed bubble
- expandable chat panel
- login
- chat API calls
- quick prompts
- iframe resize through `postMessage`

## 11. Current Known Local Dev Note

For local integration, the model server currently uses a lightweight dev implementation that preserves the same HTTP contract:

- `GET /`
- `POST /classify`
- `POST /ner`
- `POST /summarize`

This avoids heavy PyTorch downloads during local UI integration. Before final submission, the real model server path should be restored or the dev server should be moved to `model_server/main_dev.py`.
