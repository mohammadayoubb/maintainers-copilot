"""Seed local development secrets into Vault.

This script is used during local development to create the secrets that
the application expects to load from Vault.

In the final project, secrets should not be hardcoded inside the app.
Instead:
- .env only gives the app access to Vault
- Vault stores real secrets
- the API loads secrets from Vault at startup
- the API refuses to boot if required secrets are missing

Run this script after Docker Compose starts Vault.
"""

import http.client
import json
import os
from typing import Any

VAULT_HOST = "localhost"
VAULT_PORT = int(os.getenv("VAULT_PORT", "8200"))
VAULT_TOKEN = os.getenv("VAULT_ROOT_TOKEN", "root")

# Vault KV v2 stores app secrets under this path.
# The full HTTP path is /v1/secret/data/app.
SECRET_PATH = "/v1/secret/data/app"


def vault_request(method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, str]:
    """Send an HTTP request to the local Vault server.

    We use Python's built-in http.client to avoid adding extra dependencies
    just for this early foundation script.

    Args:
        method: HTTP method, such as GET or POST.
        path: Vault API path.
        body: Optional JSON body.

    Returns:
        A tuple containing the HTTP status code and response body.
    """
    connection = http.client.HTTPConnection(
        host=VAULT_HOST,
        port=VAULT_PORT,
        timeout=5,
    )

    headers = {
        "X-Vault-Token": VAULT_TOKEN,
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


def check_vault_is_running() -> None:
    """Verify that Vault is reachable before trying to seed secrets."""
    status, body = vault_request("GET", "/v1/sys/health")

    # Vault dev mode may return different health status codes.
    # Any response from this endpoint means the Vault server is reachable.
    if status not in {200, 429, 472, 473, 501, 503}:
        raise RuntimeError(f"Vault health check failed with status {status}: {body}")


def seed_app_secrets() -> None:
    """Write local development secrets into Vault.

    These are safe local dummy values.
    Real production secrets should never be committed to Git.
    """
    secrets = {
        "jwt_signing_key": "local-dev-jwt-signing-key-change-me",
        "llm_api_key": "local-dev-llm-api-key-change-me",
        "database_password": "maintainer",
        "minio_access_key": "minioadmin",
        "minio_secret_key": "minioadmin",
        "tracing_api_key": "local-dev-tracing-key-change-me",
    }

    # Vault KV v2 expects secrets to be nested under the "data" key.
    status, body = vault_request(
        "POST",
        SECRET_PATH,
        body={"data": secrets},
    )

    if status not in {200, 204}:
        raise RuntimeError(f"Failed to seed Vault secrets. Status {status}: {body}")


def main() -> None:
    """Run the Vault seed process."""
    check_vault_is_running()
    seed_app_secrets()
    print("Vault local development secrets seeded successfully.")


if __name__ == "__main__":
    main()