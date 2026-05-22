"""Public widget configuration routes.

These routes expose safe runtime widget configuration to the embedded widget.

The public widget endpoint does not expose admin-only fields or secrets.
It returns only what the browser widget needs to render itself.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_widget_service
from app.services.widget_service import WidgetService

router = APIRouter(prefix="/widgets", tags=["widgets"])


@router.get("/public/{public_widget_id}")
async def get_public_widget_config(
    public_widget_id: str,
    service: WidgetService = Depends(get_widget_service),
) -> dict[str, Any]:
    """Return safe public runtime config for an active widget."""

    widget = await service.get_widget_config(public_widget_id=public_widget_id)

    return {
        "public_widget_id": widget.public_widget_id,
        "allowed_origins": widget.allowed_origins,
        "theme": widget.theme,
        "greeting": widget.greeting,
        "enabled_tools": widget.enabled_tools,
        "is_active": widget.is_active,
    }
