"""Static file serving for the web console, plus an unauthenticated /web/config.

Kept unauthenticated so the browser UI can bootstrap (read its version and,
later, prompt for an API key) before it holds any credentials.
"""

import mimetypes
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from server import config
from server.version import __version__

router = APIRouter()


def _resolve_within(base_dir: str, filename: str) -> str:
    """Resolve ``filename`` under ``base_dir``, refusing anything that escapes it."""
    base = os.path.realpath(base_dir)
    target = os.path.realpath(os.path.join(base, filename))
    if target != base and not target.startswith(base + os.sep):
        raise HTTPException(status_code=404, detail="Not found")
    return target


@router.get("/web/config")
async def web_config() -> JSONResponse:
    return JSONResponse({"version": __version__})


@router.get("/web")
@router.get("/web/")
@router.get("/web/{filename:path}")
async def serve_web(filename: str = "") -> FileResponse:
    if not config.ENABLE_WEB_UI:
        raise HTTPException(status_code=404, detail="Web UI is disabled")

    if not filename or filename.endswith("/"):
        filename = os.path.join(filename, "index.html")

    target = _resolve_within(config.WEBUI_DIST_DIR, filename)
    if not os.path.isfile(target):
        # SPA fallback: unknown client-side routes serve index.html.
        target = _resolve_within(config.WEBUI_DIST_DIR, "index.html")
        if not os.path.isfile(target):
            raise HTTPException(status_code=404, detail="Not found")

    media_type = mimetypes.guess_type(target)[0] or "application/octet-stream"
    return FileResponse(target, media_type=media_type)
