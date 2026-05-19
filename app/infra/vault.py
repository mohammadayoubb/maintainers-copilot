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

from app.config import get_settings


def get_vault_url() -> str:
    """Build the local Vault URL from application settings.

    For local development, Vault runs inside Docker Compose on port 8200.
    The port is configurable through .env using VAULT_PORT.
    """
    settings = get_settings()
    return f"http://localhost:{settings.vault_port}"


def check_vault_reachable() -> bool:
    """Check whether the local Vault server is reachable.

    This is an early foundation check.
    Later, the app startup will use stricter checks:
    - Vault must be reachable
    - required secrets must exist
    - app refuses to boot if secrets are missing
    """
    settings = get_settings()

    try:
        connection = http.client.HTTPConnection(
            host="localhost",
            port=settings.vault_port,
            timeout=3,
        )
        connection.request("GET", "/v1/sys/health")
        response = connection.getresponse()

        # Vault health endpoint can return different success-like status codes.
        # For our foundation check, any response means Vault is reachable.
        return response.status in {200, 429, 472, 473, 501, 503}

    except OSError:
        # OSError covers connection refused, timeout, and network-related failures.
        return False

    finally:
        try:
            connection.close()
        except UnboundLocalError:
            # If the connection object was never created, there is nothing to close.
            pass