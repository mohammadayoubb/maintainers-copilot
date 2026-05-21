"""JWT authentication backend.

JWT signing key should come from Vault-loaded settings.
"""

from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy

from app.config import get_settings


bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    """Create the JWT strategy using the Vault-loaded signing key."""
    settings = get_settings()

    if not settings.jwt_signing_key:
        raise RuntimeError("JWT signing key is missing. Vault startup resolution failed.")

    return JWTStrategy(
        secret=settings.jwt_signing_key,
        lifetime_seconds=3600,
    )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)