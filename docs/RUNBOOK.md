# Maintainer's Copilot Runbook

## 1. Prerequisites

Required tools:

- Docker Desktop
- Git Bash or terminal
- Python environment if running scripts outside Docker
- Git

## 2. Start Base Services

From the project root:

```bash
docker compose up -d db redis minio vault
```

## 3. Seed Vault

Run:

```bash
python scripts/seed_vault.py
```

If the script name differs, use the project's current Vault seed script.

## 4. Run Migrations

```bash
docker compose run --rm migrate
```

## 5. Start API

```bash
docker compose up -d api
```

Check logs:

```bash
docker compose logs api --tail=80
```

Check import:

```bash
docker compose exec api python -c "from app.main import app; print('api imports ok')"
```

## 6. Start Model Server

For local integration:

```bash
docker compose up -d model-server
```

Check:

```bash
curl http://localhost:8001/
```

Test classification:

```bash
curl -X POST http://localhost:8001/classify \
  -H "Content-Type: application/json" \
  -d '{"title":"Bug when reading CSV","body":"read_csv fails with ValueError"}'
```

Expected local dev result:

```json
{"label":"bug","confidence":0.75,"model":"dev-rule-based-classifier"}
```

## 7. Start Streamlit

```bash
docker compose up -d chatbot
```

Open:

```text
http://localhost:8501
```

Login with:

```text
authuser@example.com
StrongPassword123!
```

## 8. Start Widget and Host

```bash
docker compose up -d widget host
```

Open:

```text
http://localhost:8080
```

The widget should appear as a small bubble in the bottom-right corner.

## 9. Authentication Commands

Login:

```bash
curl -X POST http://localhost:8000/auth/jwt/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'username=authuser@example.com&password=StrongPassword123!'
```

Save token:

```bash
TOKEN='PASTE_ACCESS_TOKEN_HERE'
```

Check current user:

```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

## 10. Chat Smoke Tests

### Classification

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message":"Classify this issue: read_csv fails with ValueError"}'
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
  -d '{"message":"Summarize this thread: User reports read_csv failing. Maintainer asks for reproduction."}'
```

### RAG

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message":"How should pandas maintainers handle a read_csv parsing bug?"}'
```

### Memory Write

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message":"Remember that this user prefers concise maintainer answers."}'
```

## 11. Redis Short-Term Memory Check

List messages:

```bash
docker compose exec redis redis-cli LRANGE chat:conversation:19:messages 0 -1
```

Check TTL:

```bash
docker compose exec redis redis-cli TTL chat:conversation:19:messages
```

Expected TTL:

```text
A number between 1 and 1800
```

## 12. Database Checks

List users:

```bash
docker compose exec db psql -U maintainer -d maintainers_copilot -c "SELECT id, email, role FROM users ORDER BY id;"
```

Promote user to admin:

```bash
docker compose exec db psql -U maintainer -d maintainers_copilot -c "UPDATE users SET role = 'admin' WHERE email = 'authuser@example.com';"
```

Check memories:

```bash
docker compose exec db psql -U maintainer -d maintainers_copilot -c "SELECT id, user_id, memory_type, content FROM memories ORDER BY id DESC LIMIT 5;"
```

## 13. Test Commands

Run redaction and exception tests:

```bash
pytest tests/test_redaction.py tests/test_exception_handlers.py -q
```

Run API import check:

```bash
docker compose exec api python -c "from app.main import app; print('api imports ok')"
```

## 14. Common Issues

### Unauthorized

Cause:

- expired token
- token lost after restart
- shell variable empty

Fix:

```bash
curl -X POST http://localhost:8000/auth/jwt/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'username=authuser@example.com&password=StrongPassword123!'
```

Then reset `TOKEN`.

### Model Server Unreachable

Check:

```bash
docker compose ps
docker compose logs model-server --tail=80
```

Start:

```bash
docker compose up -d model-server
```

### CORS Error in Widget

Check origins in `app/main.py`.

Local widget/host origins:

```text
http://localhost:5174
http://localhost:8080
```

### Redis Key Missing

If TTL returns `-2`, the key does not exist or expired.

Send a new chat message and check the new conversation ID.

### Redis Key Has No TTL

If TTL returns `-1`, the key exists but has no expiry.

Check `ShortTermMemoryService.append_message()`.
