"""Widget service.

This service owns widget configuration business logic.
Admins will later call this through API/Streamlit routes.
"""

from typing import Any

from app.domain.errors import NotFoundError, ValidationDomainError
from app.repositories.widget_repo import WidgetRepository
from app.services.audit_service import AuditService


class WidgetService:
    """Business logic for embeddable widget configuration."""

    def __init__(
        self,
        *,
        widget_repo: WidgetRepository,
        audit_service: AuditService,
    ) -> None:
        """Store repository and service dependencies."""
        self.widget_repo = widget_repo
        self.audit_service = audit_service

    async def create_widget_config(
        self,
        *,
        actor_id: int | None,
        allowed_origins: list[str],
        theme: dict[str, Any],
        greeting: str,
        enabled_tools: list[str],
    ):
        """Create a widget config and audit the change."""
        self._validate_allowed_origins(allowed_origins)

        widget = await self.widget_repo.create_widget_config(
            allowed_origins=allowed_origins,
            theme=theme,
            greeting=greeting,
            enabled_tools=enabled_tools,
            created_by=actor_id,
        )

        await self.audit_service.record(
            actor_id=actor_id,
            action="widget_config_create",
            target_type="widget_config",
            target_id=widget.public_widget_id,
            metadata={
                "allowed_origins": allowed_origins,
                "enabled_tools": enabled_tools,
            },
        )

        return widget

    async def get_widget_config(self, *, public_widget_id: str):
        """Return an active widget config or raise a domain error."""
        widget = await self.widget_repo.get_by_public_id(
            public_widget_id=public_widget_id,
        )

        if widget is None:
            raise NotFoundError("Widget configuration not found.")

        return widget

    async def list_widget_configs(self, *, limit: int = 50):
        """List recent widget configs."""
        return await self.widget_repo.list_widget_configs(limit=limit)

    def _validate_allowed_origins(self, allowed_origins: list[str]) -> None:
        """Validate widget allowed origins before saving config."""
        if not allowed_origins:
            raise ValidationDomainError("At least one allowed origin is required.")

        for origin in allowed_origins:
            if not origin.startswith(("http://", "https://")):
                raise ValidationDomainError(
                    "Allowed origins must start with http:// or https://."
                )