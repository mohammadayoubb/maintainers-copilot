# Maintainer's Copilot Security Notes

## 1. Security Goals

The project handles user-submitted issue text, stack traces, tokens, and credentials. Security focuses on:

- safe secret handling
- redaction
- authentication
- authorization
- safe memory writes
- safe errors
- widget origin control

## 2. Authentication

Authentication uses `fastapi-users` with JWT.

Login endpoint:

```text
POST /auth/jwt/login
```

Current user endpoint:

```text
GET /auth/me
```

JWT tokens are sent using:

```text
Authorization: Bearer <token>
```

## 3. JWT Secret

The JWT signing key is loaded from Vault during startup.

The API should fail startup if required Vault secrets are missing.

## 4. Roles

Current roles:

```text
user
admin
```

Admin-only functionality includes widget configuration routes and admin development operations.

## 5. Vault

Vault stores secrets such as:

- JWT signing key
- API keys
- database-related secrets
- MinIO-related secrets
- tracing provider keys if used

The application should not hardcode production secrets in source code.

## 6. Redaction

Redaction is implemented in:

```text
app/infra/redaction.py
```

Redaction should happen before sensitive content is written to:

- logs
- traces
- memory
- saved message content
- retrieved snapshots

## 7. Redaction Patterns

Patterns should include:

- OpenAI-style keys: `sk-...`
- GitHub tokens: `ghp_...`, `github_pat_...`
- bearer tokens
- JWT-like tokens
- database URLs with passwords
- password-like key/value strings
- private keys

## 8. Redaction Test

The project includes:

```text
tests/test_redaction.py
```

The required security behavior:

```text
A fake API key should not appear unredacted in stored or emitted text.
```

## 9. Long-Term Memory Safety

Long-term memory writes are explicit only.

The chatbot writes memory only when the user clearly asks:

```text
Remember that ...
```

or:

```text
Remember: ...
```

This prevents hidden or unexpected memory writes.

Each long-term memory write creates an audit log row.

## 10. Short-Term Memory Safety

Short-term memory is stored in Redis with a TTL.

Current TTL:

```text
1800 seconds = 30 minutes
```

Reason:

- temporary conversation context should not live forever
- active conversations stay alive because each append refreshes the TTL

Redis key format:

```text
chat:conversation:{conversation_id}:messages
```

## 11. Error Handling

Domain exceptions are mapped at the API boundary.

Users should receive structured errors instead of stack traces.

Examples:

| Error | Status |
|---|---:|
| Not found | 404 |
| Permission denied | 403 |
| Validation error | 400 |
| Tool failure | 502 |

## 12. Tool Failure Recovery

Chatbot tool failures should not crash the whole chat experience.

If a tool is unavailable, the chatbot returns a safe fallback message.

Example:

```text
One of the chatbot tools is temporarily unavailable, so I could not complete that tool call right now. The message was still saved.
```

## 13. CORS

Local demo CORS allows:

```text
http://localhost:5174
http://localhost:8080
http://127.0.0.1:5174
http://127.0.0.1:8080
```

This is for local widget and host demo.

Future production behavior should enforce CORS based on widget configuration stored in the database.

## 14. Widget Security

The widget is embedded using:

```html
<script src="http://localhost:8000/widget.js" data-widget-id="demo-widget"></script>
```

The loader injects an iframe.

Future production hardening should include:

- allowed origins from database
- `Content-Security-Policy` with `frame-ancestors`
- per-widget enabled tools
- runtime widget theme/config
- no hardcoded demo credentials

## 15. Local Demo Credentials

The local demo uses:

```text
authuser@example.com
StrongPassword123!
```

This is only for local development/demo. It should not be used as a production credential.

## 16. Known Final-Day Risk

The model server was temporarily switched to a lightweight local development implementation to avoid heavy PyTorch downloads during UI integration.

Before final submission:

- restore the real model server, or
- move the dev version to `model_server/main_dev.py` and keep the real `model_server/main.py`

This should be documented clearly in the runbook if both modes remain.
