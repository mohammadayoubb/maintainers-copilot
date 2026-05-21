"""Repository for embeddable widget configuration database operations."""

from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import WidgetConfig


class WidgetRepository:
    """Database access layer for widget configuration rows."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the database session used by this repository."""
        self.session = session

    async def create_widget_config(
        self,
        *,
        allowed_origins: list[str],
        theme: dict[str, Any],
        greeting: str,
        enabled_tools: list[str],
        created_by: int | None,
    ) -> WidgetConfig:
        """Create a widget configuration with a public widget ID."""
        widget = WidgetConfig(
            public_widget_id=f"w_{uuid4().hex}",
            allowed_origins=allowed_origins,
            theme=theme,
            greeting=greeting,
            enabled_tools=enabled_tools,
            created_by=created_by,
            is_active=True,
        )

        self.session.add(widget)
        await self.session.flush()
        await self.session.refresh(widget)

        return widget

    async def get_by_public_id(self, *, public_widget_id: str) -> WidgetConfig | None:
        """Fetch an active widget config by public widget ID."""
        statement = select(WidgetConfig).where(
            WidgetConfig.public_widget_id == public_widget_id,
            WidgetConfig.is_active.is_(True),
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_widget_configs(self, *, limit: int = 50) -> list[WidgetConfig]:
        """Return recent widget configs."""
        statement = (
            select(WidgetConfig)
            .order_by(WidgetConfig.created_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(statement)
        return list(result.scalars().all())