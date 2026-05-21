# Maintainer's Copilot

The assistant helps maintainers triage GitHub issues by combining:

- issue classification
- code-shaped entity extraction
- issue/thread summarization
- advanced RAG over project documentation and resolved issues
- authenticated chat with memory
- Streamlit internal/admin UI
- embeddable widget support
- redaction, exception handling, and production-style architecture

The chosen dataset/repository for this project is:

```text
pandas-dev/pandas
```

The project maps GitHub issue labels into four project labels:

```text
bug
feature
docs
question
```

---

## Project Goal

The goal is to build a production-shaped Maintainer's Copilot that an open-source maintainer can use while reviewing issues.

A maintainer can ask the chatbot to:

- classify an issue as `bug`, `feature`, `docs`, or `question`
- extract useful code-shaped entities such as files, functions, errors, versions, and constants
- summarize issue threads
- retrieve similar resolved issues or documentation using RAG
- remember explicit maintainer preferences
- use the assistant through either Streamlit or an embedded host widget

---

## Architecture Overview

The project follows a layered backend architecture.

```text
User / Maintainer
   |
   | uses
   v
Streamlit App OR Embedded Widget
   |
   | HTTP
   v
FastAPI API
   |
   | calls services
   v
app/services/
   |
   | coordinates repositories and infra adapters
   v
Repositories + Infra
   |
   | database / Redis / Vault / model-server / RAG files
   v
External services
```

### Layering Rules

```text
app/api/
```

Routes only handle HTTP concerns. They parse requests, call services, and return responses.

```text
app/services/
```

Services contain business logic. They coordinate repositories, infra adapters, memory, model tools, and RAG.

```text
app/repositories/
```

Repositories own database access only.

```text
app/domain/
```

Domain files contain business models and domain errors.

```text
app/infra/
```

Infra files contain external adapters such as Vault, Redis, redaction, startup checks, and the model-server client.

---

## Main Services

The Docker Compose stack includes:

| Service | Purpose |
|---|---|
| `api` | Main FastAPI backend for auth, chat, tools, memory, widget loader, and RAG orchestration |
| `model-server` | Local ML/NLP inference server for `/classify`, `/ner`, and `/summarize` |
| `chatbot` | Streamlit internal/admin chatbot UI |
| `widget` | Static widget frontend served by nginx |
| `host` | Demo host app that embeds the widget |
| `migrate` | Alembic migration runner |
| `db` | Postgres with pgvector support |
| `redis` | Short-term conversation memory and cache |
| `minio` | Blob/artifact storage service |
| `vault` | Local development secrets manager |

---

## Fresh Clone Startup

This project uses **Option A startup**: infrastructure is started first, Vault is seeded manually, migrations are run, and then the application services are started.

This is intentional because the API refuses to boot if Vault secrets are missing.

### 1. Copy the environment file

From the project root:

```bash
cp .env.example .env
```

The `.env.example` file contains local development ports and Vault configuration.

Secrets such as the JWT signing key are not hardcoded in the app. They are loaded from Vault during API startup.

---

### 2. Build the Docker images

```bash
docker compose build
```

---

### 3. Start infrastructure services first

```bash
docker compose up -d vault db redis minio model-server
```

These services provide:

- Vault for local development secrets
- Postgres for users, conversations, messages, memories, widgets, and audit logs
- Redis for short-term chat memory
- MinIO for blob/artifact storage
- model-server for the chatbot tools

---

### 4. Seed Vault

Run the Vault seed script from your laptop:

```bash
VAULT_HOST=localhost VAULT_PORT=8200 VAULT_ROOT_TOKEN=root python scripts/seed_vault.py
```

On Windows Git Bash, this command should be run from the project root.

Vault dev mode can lose secrets if the container is recreated, so if the API later fails with a Vault `404`, run the seed command again.

You can verify that Vault has the app secrets with:

```bash
curl -H "X-Vault-Token: root" http://localhost:8200/v1/secret/data/app
```

Do not paste or commit real secrets.

---

### 5. Run database migrations

```bash
docker compose run --rm migrate
```

This applies Alembic migrations to Postgres.

---

### 6. Start application services

```bash
docker compose up -d api chatbot widget host
```

---

### 7. Check running containers

```bash
docker compose ps
```

Expected main services:

```text
api
model-server
chatbot
widget
host
db
redis
minio
vault
```

---

## Local URLs

After startup, open:

| URL | Purpose |
|---|---|
| http://localhost:8000/docs | FastAPI Swagger UI |
| http://localhost:8001 | model-server health check |
| http://localhost:8501 | Streamlit chatbot UI |
| http://localhost:5174 | Direct widget page |
| http://localhost:8080 | Demo host app embedding the widget |
| http://localhost:9001 | MinIO console |
| http://localhost:8200 | Vault API/UI |

---

## Important Startup Note

Running:

```bash
docker compose up
```

starts containers, but from a completely fresh/reset Vault it does not automatically seed Vault.

For a fresh clone or after Vault reset, use the full startup sequence:

```bash
cp .env.example .env
docker compose build
docker compose up -d vault db redis minio model-server
VAULT_HOST=localhost VAULT_PORT=8200 VAULT_ROOT_TOKEN=root python scripts/seed_vault.py
docker compose run --rm migrate
docker compose up -d api chatbot widget host
```

If the API logs show:

```text
Failed to read app secrets from Vault. Status 404
```

then Vault is running but not seeded. Re-run:

```bash
VAULT_HOST=localhost VAULT_PORT=8200 VAULT_ROOT_TOKEN=root python scripts/seed_vault.py
docker compose restart api
```

---

## Local Model Server Note

For local Docker integration, the `model-server` service runs:

```text
model_server.main_dev:app
```

This is a lightweight development server that preserves the same HTTP contract as the real model server:

- `POST /classify`
- `POST /ner`
- `POST /summarize`

It avoids heavy PyTorch downloads during local smoke testing.

The production-shaped entrypoint remains:

```text
model_server/main.py
```

The fine-tuned DistilBERT model, metrics, and comparison results are kept in the ML artifacts and documentation.

---

## Authentication

The backend uses:

- `fastapi-users`
- JWT authentication
- email/password login
- user/admin roles
- Vault-loaded JWT signing key

The known local test user used during development is:

```text
authuser@example.com
StrongPassword123!
```

If needed, users can be inspected with:

```bash
docker compose exec db psql -U maintainer -d maintainers_copilot -c "SELECT id, email, role FROM users ORDER BY id;"
```

To make a user admin locally:

```bash
docker compose exec db psql -U maintainer -d maintainers_copilot -c "UPDATE users SET role = 'admin' WHERE email = 'authuser@example.com';"
```

---

## Login and API Smoke Tests

### Login

```bash
curl -X POST http://localhost:8000/auth/jwt/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'username=authuser@example.com&password=StrongPassword123!'
```

Copy the returned access token:

```bash
TOKEN='PASTE_ACCESS_TOKEN_HERE'
```

### Check authenticated user

```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

---

## Chatbot Smoke Tests

### Classification

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message":"Classify this issue: read_csv fails with ValueError in parser.py"}'
```

### Entity Extraction

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message":"Extract entities from this issue: read_csv() fails with ValueError in parser.py"}'
```

### Summarization

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message":"Summarize this thread: read_csv fails when parsing malformed CSV files. Maintainer says it needs a reproducible example."}'
```

### RAG

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message":"How should pandas maintainers handle a read_csv parsing bug?"}'
```

### Explicit Memory Write

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message":"Remember that this maintainer prefers concise answers with reproduction steps."}'
```

---

## Redis Short-Term Memory Check

The chatbot stores short-term conversation state in Redis.

Example key format:

```text
chat:conversation:{conversation_id}:messages
```

Check messages:

```bash
docker compose exec redis redis-cli LRANGE chat:conversation:19:messages 0 -1
```

Check TTL:

```bash
docker compose exec redis redis-cli TTL chat:conversation:19:messages
```

The TTL is currently:

```text
1800 seconds
```

That is 30 minutes.

This is long enough for a normal chat pause, but short enough to avoid keeping temporary conversation state forever.

---

## Streamlit UI

Open:

```text
http://localhost:8501
```

The Streamlit app supports:

- register
- login
- JWT storage in session state
- authenticated `/auth/me`
- chat requests through `/chat`
- conversation continuation with `conversation_id`
- quick test prompts
- logout

---

## Widget and Host App

The widget has two ways to view it.

### Direct widget page

```text
http://localhost:5174
```

This opens the widget UI directly.

### Demo host app

```text
http://localhost:8080
```

The host page embeds the widget through the API loader script:

```html
<script src="http://localhost:8000/widget.js" data-widget-id="demo-widget"></script>
```

The host page depends on the API being fully started. If `localhost:8000` is not working, the widget bubble will not appear on `localhost:8080`.

### Widget loader check

```bash
curl http://localhost:8000/widget.js
```

Expected result: JavaScript output.

---

## ML Classification Track

The classification task compares three approaches on the same label space:

```text
bug
feature
docs
question
```

The three approaches are:

1. Classical ML baseline
2. Fine-tuned transformer
3. LLM baseline

### Classical ML Baseline

The classical baseline uses a traditional machine learning classifier over text features.

Typical pipeline:

```text
TF-IDF + classifier
```

### Fine-Tuned Transformer

The fine-tuned model is:

```text
distilbert-base-uncased
```

It is used for issue classification.

Important note:

```text
The fine-tuned DistilBERT model is used only for issue classification.
It is not used for RAG embeddings.
```

### LLM Baseline

The LLM baseline classifies issues with a prompt and compares its performance against the classical ML and transformer approaches.

### Deployment Choice

The project keeps the fine-tuned transformer as the main evaluated classifier choice because it provides a strong balance of classification quality, reproducibility, latency, and cost compared with using an LLM for every classification request.

For local Docker smoke tests, the lightweight dev model server is used only to avoid heavy local PyTorch downloads.

---

## RAG Track

The RAG system uses project documentation and resolved pandas issues.

Important RAG files include:

```text
rag/chunking.py
rag/embeddings.py
rag/retrieval.py
rag/rerank.py
rag/query_transform.py
rag/ingest.py
rag/pipeline.py
rag/build_embeddings.py
rag/compare_embeddings.py
```

The RAG corpus includes resolved pandas issues with maintainer comments.

Important data files include:

```text
rag/data/resolved_issues_with_comments.jsonl
rag/data/resolved_issues.jsonl
rag/data/chunks.jsonl
rag/data/rag_golden_suggestions.json
rag/data/embeddings_BAAI_bge-small-en.jsonl
```

---

## RAG Evaluation

The RAG golden set contains:

```text
25 examples
```

The final evaluated configuration:

```text
Embedding model: BAAI/bge-small-en
Dense weight: 0.8
Sparse weight: 0.2
```

Final RAG evaluation result:

```text
hit@5 = 1.0000
MRR@10 ≈ 0.7307
skipped_examples = 0
```

The RAG service tries real BGE embedding retrieval first. If local dependencies such as `sentence-transformers` are unavailable, it falls back to lightweight sparse keyword retrieval over `chunks.jsonl`.

That fallback is for local integration and graceful degradation. It does not replace the evaluated RAG pipeline.

---

## Query Transformation

The project uses deterministic rule-based query expansion.

Example:

```text
csv
```

expands with terms such as:

```text
read_csv
parser
DataFrame
delimiter
```

Reason:

- deterministic
- cheap
- reproducible
- fast
- good for technical GitHub issue retrieval
- preserves important code terms

---

## Redaction

The project includes a redaction layer in:

```text
app/infra/redaction.py
```

Redaction protects logs, traces, memory writes, and other service-boundary outputs.

The test file:

```text
tests/test_redaction.py
```

checks that sensitive values such as fake API keys are not left unredacted.

Run:

```bash
pytest tests/test_redaction.py -q
```

---

## Exception Handling

Domain exceptions are defined in:

```text
app/domain/errors.py
```

API exception mapping is handled in:

```text
app/api/exception_handlers.py
```

Current mapping:

| Domain Error | HTTP Status |
|---|---:|
| `NotFoundError` | 404 |
| `PermissionDeniedError` | 403 |
| `ValidationDomainError` | 400 |
| `ToolFailureError` | 502 |

Run:

```bash
pytest tests/test_exception_handlers.py -q
```

The goal is that users see safe structured errors, not stack traces.

---

## Tests

Run the core tests:

```bash
pytest tests/test_redaction.py tests/test_exception_handlers.py -q
```

Run an API import check:

```bash
docker compose exec api python -c "from app.main import app; print('api imports ok')"
```

---

## Useful Debug Commands

### Check all containers

```bash
docker compose ps
```

### API logs

```bash
docker compose logs api --tail=120
```

### Model server logs

```bash
docker compose logs model-server --tail=80
```

### Restart API

```bash
docker compose restart api
```

### Rebuild model server only

```bash
docker compose build --no-cache model-server
docker compose up -d model-server api
```

### Check model server

```bash
curl http://localhost:8001/
```

### Check API docs

```bash
curl -I http://localhost:8000/docs
```

### Check widget loader

```bash
curl http://localhost:8000/widget.js
```

---

## Common Errors

### API starts but `/docs` does not load

Check logs:

```bash
docker compose logs api --tail=120
```

If you see:

```text
Failed to read app secrets from Vault. Status 404
```

then seed Vault again:

```bash
VAULT_HOST=localhost VAULT_PORT=8200 VAULT_ROOT_TOKEN=root python scripts/seed_vault.py
docker compose restart api
```

---

### Host page loads but widget bubble does not show

Check API:

```bash
curl -I http://localhost:8000/docs
```

Check widget loader:

```bash
curl http://localhost:8000/widget.js
```

The host page at `localhost:8080` depends on the API serving `/widget.js`.

---

### Model server returns `not_configured`

That means Docker is probably running:

```text
model_server.main:app
```

instead of:

```text
model_server.main_dev:app
```

Check `docker-compose.yml` and confirm the model-server command is:

```text
uvicorn model_server.main_dev:app --host 0.0.0.0 --port 8001
```

Then rebuild:

```bash
docker compose build --no-cache model-server
docker compose up -d model-server api
```

---

## Project Documentation

Additional documentation is located in:

```text
docs/
```

Expected final documentation files:

```text
docs/ARCH.md
docs/DECISIONS.md
docs/RUNBOOK.md
docs/EVALS.md
docs/SECURITY.md
```

These documents explain:

- system architecture
- major decisions and tradeoffs
- startup and debugging process
- evaluation design and results
- Vault, redaction, JWT, audit logs, and safe logging

---

## Final Submission Checklist

Before submission:

```bash
git status
```

Expected:

```text
nothing to commit, working tree clean
```

Run tests:

```bash
pytest tests/test_redaction.py tests/test_exception_handlers.py -q
```

Check API import:

```bash
docker compose exec api python -c "from app.main import app; print('api imports ok')"
```

Check model server:

```bash
curl http://localhost:8001/
```

Check API:

```bash
curl -I http://localhost:8000/docs
```

Check widget loader:

```bash
curl http://localhost:8000/widget.js
```

After final commits:

```bash
git push origin main
```

Create the final tag:

```bash
git tag v0.1.0-week7
git push origin v0.1.0-week7
```

