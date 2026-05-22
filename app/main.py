"""Main FastAPI application entry point.

This file creates the main API application and registers:
- startup checks
- exception handlers
- API routers

The app startup uses FastAPI lifespan so infrastructure checks run before
the API is considered ready.

For now, startup checks verify that:
- Vault is reachable
- required Vault secrets exist

Later, startup checks can also verify:
- classifier model artifact exists
- classifier SHA-256 matches the model card
- tracing backend is configured
- eval thresholds are not disabled
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

from app.api.exception_handlers import domain_error_handler
from app.api.routes.health import router as health_router
from app.domain.errors import DomainError
from app.infra.startup_checks import run_startup_checks
from app.api.routes import day4_dev
from app.api.routes.classification import router as classification_router
from app.api.routes.tools import router as tools_router
from app.api.routes import auth as auth_routes
from app.auth.backend import auth_backend
from app.auth.schemas import UserCreate, UserRead, UserUpdate
from app.auth.users import fastapi_users
from app.api.routes.chat import router as chat_router
from app.api.routes import widget_loader
from app.api.routes import widget_config

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Run startup and shutdown logic for the FastAPI app.

    FastAPI calls this function when the API starts.

    If run_startup_checks() raises an error, the API refuses to boot.
    This matches the project requirement that unsafe or incomplete
    infrastructure should block startup instead of failing later at runtime.
    """
    run_startup_checks()

    yield


# Create the FastAPI application object.
# This is the object Uvicorn runs when we start the API container.
app = FastAPI(
    title="Maintainer's Copilot API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://localhost:8080",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Register the global domain error handler.
# Any DomainError raised inside routes/services will be converted into
# a safe structured HTTP response.
app.add_exception_handler(DomainError, domain_error_handler)


app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

app.include_router(auth_routes.router)


# Register the health router.
# This makes GET /health available.
app.include_router(health_router)
app.include_router(classification_router)
app.include_router(tools_router)
app.include_router(day4_dev.router)
app.include_router(chat_router)
app.include_router(widget_loader.router)
app.include_router(widget_config.router)
