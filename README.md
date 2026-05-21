# Maintainer's Copilot

Maintainer's Copilot is a Week 7 AI Engineering project.

It is an authenticated assistant for open-source maintainers. The system helps with:

- GitHub issue classification
- code-shaped entity extraction
- issue thread summarization
- RAG over project docs and resolved issues
- chatbot memory
- embeddable React widget support
- evaluation gates in CI

## Fresh Clone Startup

This project is designed to run locally with Docker Compose.

### 1. Create the environment file

```bash
cp .env.example .env

## Current Phase

The project is currently in the Day 1 Foundations phase.

Completed foundation work:

- Project folder structure
- FastAPI API skeleton
- Model server skeleton
- Streamlit skeleton
- Docker Compose base stack
- Postgres with pgvector
- Redis
- MinIO
- Vault
- Alembic migrations
- Vault seed script
- Startup infrastructure checks
- Initial issue database tables

## Services

The Docker Compose stack includes:

| Service | Purpose |
|---|---|
| `api` | Main FastAPI backend |
| `model-server` | ML/NLP inference server |
| `chatbot` | Streamlit internal/admin app |
| `migrate` | Runs Alembic migrations |
| `db` | Postgres 16 with pgvector |
| `redis` | Short-term memory and cache |
| `minio` | Blob/artifact storage |
| `vault` | Local development secrets manager |

## Local Setup

Copy the example environment file:

```bash
cp .env.example .env


