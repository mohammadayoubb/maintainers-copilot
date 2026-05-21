"""Widget loader routes.

This route serves the small JavaScript loader that a host page embeds.

The host page uses:

<script src="http://localhost:8000/widget.js" data-widget-id="demo-widget"></script>

The loader injects an iframe pointing to the widget UI.
"""

from fastapi import APIRouter, Response

router = APIRouter(tags=["widget-loader"])


@router.get("/widget.js")
async def widget_loader() -> Response:
    """Serve the embeddable widget loader script."""
    script = """
(function () {
  const currentScript = document.currentScript;
  const widgetId = currentScript?.getAttribute("data-widget-id") || "demo-widget";

  const iframe = document.createElement("iframe");
  iframe.src = "http://localhost:5174/?widget_id=" + encodeURIComponent(widgetId);
  iframe.title = "Maintainer Copilot Widget";

  iframe.style.position = "fixed";
  iframe.style.right = "24px";
  iframe.style.bottom = "24px";
  iframe.style.width = "74px";
  iframe.style.height = "74px";
  iframe.style.border = "0";
  iframe.style.borderRadius = "18px";
  iframe.style.zIndex = "999999";
  iframe.style.background = "transparent";

  window.addEventListener("message", function (event) {
    if (!event.data || event.data.type !== "maintainer-copilot-resize") {
      return;
    }

    if (event.data.height) {
      iframe.style.height = event.data.height + "px";
    }

    if (event.data.width) {
      iframe.style.width = event.data.width + "px";
    }
  });

  document.body.appendChild(iframe);
})();
"""

    return Response(
        content=script,
        media_type="application/javascript",
        headers={
            "Cache-Control": "no-store",
        },
    )