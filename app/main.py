"""Main FastAPI application entry point.

This file creates the main API application and registers all API routers.
For now, this file registers:
- health route
- domain error handler

Later, this file will also include startup checks, auth routes, chat routes,
memory routes, widget routes, and tracing middleware.
"""

from fastapi import FastAPI

from app.api.exception_handlers import domain_error_handler
from app.api.routes.health import router as health_router
from app.domain.errors import DomainError

# Create the FastAPI application object.
# This is the object Uvicorn runs when we start the API container.
app = FastAPI(
    title="Maintainer's Copilot API",
    version="0.1.0",
)


# Register the global domain error handler.
# Any DomainError raised inside routes/services will be converted into
# a safe structured HTTP response.
app.add_exception_handler(DomainError, domain_error_handler)


# Register the health router.
# This makes GET /health available.
app.include_router(health_router)