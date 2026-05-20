"""Vault infrastructure adapter.

This file owns communication with HashiCorp Vault.

Vault is used to store secrets such as:
- JWT signing key
- LLM API key
- database password
- MinIO secret key
- tracing backend keys

Important architecture rule:
Only infra files should talk directly to Vault.
API routes and services should not use Vault directly.
"""

import http.client
import json
from typing import Any

from app.config import get_settings


def get_vault_host() -> str:
    """Return the configured Vault host.

    From the laptop, this is usually localhost.
    Inside Docker Compose, this is the Vault service name: vault.
    """
    settings = get_settings()
    return settings.vault_host


def get_vault_url() -> str:
    """Build the local Vault URL from application settings."""
    settings = get_settings()
    return f"http://{get_vault_host()}:{settings.vault_port}"


def vault_request(method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, str]:
    """Send an HTTP request to Vault.

    This small helper keeps Vault HTTP communication in one place.

    Args:
        method: HTTP method, such as GET or POST.
        path: Vault API path, for example /v1/sys/health.
        body: Optional JSON body.

    Returns:
        A tuple containing the HTTP status code and response body.
    """
    settings = get_settings()

    connection = http.client.HTTPConnection(
        host=get_vault_host(),
        port=settings.vault_port,
        timeout=5,
    )

    headers = {
        "X-Vault-Token": settings.vault_root_token,
        "Content-Type": "application/json",
    }

    payload = json.dumps(body).encode("utf-8") if body is not None else None

    try:
        connection.request(method, path, body=payload, headers=headers)
        response = connection.getresponse()
        response_body = response.read().decode("utf-8")
        return response.status, response_body

    finally:
        connection.close()


def check_vault_reachable() -> bool:
    """Check whether the local Vault server is reachable.

    This is used by startup checks to verify that Vault is available.
    The final project requires the app to refuse to boot if Vault is unreachable.
    """
    try:
        status, _body = vault_request("GET", "/v1/sys/health")
        return status in {200, 429, 472, 473, 501, 503}

    except OSError:
        return False


def read_app_secrets() -> dict[str, str]:
    """Read application secrets from Vault.

    The seed script writes secrets to:
    secret/app

    Vault KV v2 exposes that path through:
    /v1/secret/data/app

    Returns:
        A dictionary of secret names and secret values.

    Raises:
        RuntimeError: If Vault cannot return the expected secret payload.
    """
    status, body = vault_request("GET", "/v1/secret/data/app")

    if status != 200:
        raise RuntimeError(f"Failed to read app secrets from Vault. Status {status}: {body}")

    payload = json.loads(body)

    try:
        secrets = payload["data"]["data"]
    except KeyError as exc:
        raise RuntimeError("Vault response did not contain expected secret data.") from exc

    return {key: str(value) for key, value in secrets.items()}


def require_app_secrets(required_keys: list[str]) -> dict[str, str]:
    """Read secrets from Vault and verify required keys exist.

    Args:
        required_keys: Secret names that must exist.

    Returns:
        All loaded secrets.

    Raises:
        RuntimeError: If any required secret is missing.
    """
    secrets = read_app_secrets()

    missing_keys = [key for key in required_keys if not secrets.get(key)]

    if missing_keys:
        raise RuntimeError(f"Missing required Vault secrets: {', '.join(missing_keys)}")

    return secrets