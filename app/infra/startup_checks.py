"""Application startup checks.

This file contains validation checks that run when the API starts.

The Week 7 project requires the app to refuse to boot if important
infrastructure or required configuration is missing.

For now, we check:
- Vault is reachable
- required Vault secrets exist

Later, this file can also check:
- classifier weights exist
- classifier SHA-256 matches the model card
- tracing backend is configured
- eval thresholds are not disabled or set to zero
"""

from app.infra.vault import (
    check_vault_reachable,
    load_app_secrets_into_settings,
    require_app_secrets,
)
# These are the secrets the app expects Vault to contain.
# They are seeded locally by scripts/seed_vault.py.
REQUIRED_VAULT_SECRETS = [
    "jwt_signing_key",
    "llm_api_key",
    "database_password",
    "minio_access_key",
    "minio_secret_key",
    "tracing_api_key",
]


def run_startup_checks() -> None:
    """Run required startup checks.

    Raises:
        RuntimeError: If a required dependency or secret is missing.

    Why raise errors?
    Because the project requires the API to refuse to boot when required
    infrastructure is unavailable or unsafe.
    """
    if not check_vault_reachable():
        raise RuntimeError("Vault is unreachable. Refusing to boot.")

    require_app_secrets(REQUIRED_VAULT_SECRETS)
    load_app_secrets_into_settings()