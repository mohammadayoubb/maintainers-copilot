"""Widget loader route.

This route serves the script that a host page embeds with one script tag.
The script injects an iframe that points to the standalone React widget.
"""

from fastapi import APIRouter, Response

router = APIRouter(tags=["widget-loader"])


@router.get("/widget.js")
def widget_loader() -> Response:
    """Return the JavaScript loader used by host websites."""

    script = """
(function () {
  const currentScript = document.currentScript;
  const widgetId = currentScript?.dataset?.widgetId || "demo-widget";

  const iframe = document.createElement("iframe");

  iframe.src = "http://localhost:5174?widget_id=" + encodeURIComponent(widgetId);
  iframe.title = "Maintainer's Copilot Widget";

  iframe.style.position = "fixed";
  iframe.style.right = "24px";
  iframe.style.bottom = "24px";
  iframe.style.width = "76px";
  iframe.style.height = "76px";
  iframe.style.border = "0";
  iframe.style.zIndex = "999999";
  iframe.style.background = "transparent";
  iframe.style.overflow = "hidden";

  iframe.setAttribute("allowtransparency", "true");

  document.body.appendChild(iframe);

  window.addEventListener("message", function (event) {
    if (!event.data || event.data.type !== "maintainers-copilot:resize") {
      return;
    }

    const width = Number(event.data.width || 76);
    const height = Number(event.data.height || 76);

    iframe.style.width = width + "px";
    iframe.style.height = height + "px";
  });
})();
"""

    return Response(
        content=script,
        media_type="application/javascript",
        headers={
            "Cache-Control": "no-store"
        },
    )