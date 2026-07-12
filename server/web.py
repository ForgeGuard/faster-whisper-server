"""Static file serving for the web console, plus an unauthenticated /web/config.

Kept unauthenticated so the browser UI can bootstrap (read its version and,
later, prompt for an API key) before it holds any credentials.

Fingerprinted bundles under /web/assets are served by a StaticFiles mount (set
up in main.py alongside this router) so they get ETag/Last-Modified conditional
handling (304s) for free; this router covers the redirect, config, index.html,
and the SPA fallback.
"""

import mimetypes
import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

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
    return JSONResponse(
        {
            "version": __version__,
            "root_path": os.environ.get("UVICORN_ROOT_PATH", ""),
            "max_upload_bytes": config.MAX_UPLOAD_BYTES,
            "model": config.MODEL_SIZE,
        }
    )


@router.get("/web")
async def web_redirect(request: Request) -> RedirectResponse:
    # Redirect the slash-less path to /web/ so the SPA's relative asset URLs
    # (built with Vite base './') resolve under /web/ instead of the site root.
    # Appending to the path as seen keeps this correct behind a reverse-proxy prefix.
    return RedirectResponse(url=request.url.path + "/", status_code=308)


@router.get("/web/")
@router.get("/web/{filename:path}")
async def serve_web(filename: str = "") -> FileResponse:
    if not filename or filename.endswith("/"):
        filename = os.path.join(filename, "index.html")

    target = _resolve_within(config.WEBUI_DIST_DIR, filename)
    if not os.path.isfile(target):
        # A dotted basename looks like an asset fetch — a real 404 beats
        # serving index.html as a script/stylesheet. Extensionless paths are
        # SPA client routes and fall back to index.html.
        if "." in os.path.basename(filename):
            raise HTTPException(status_code=404, detail="Not found")
        target = _resolve_within(config.WEBUI_DIST_DIR, "index.html")
        if not os.path.isfile(target):
            raise HTTPException(status_code=404, detail="Not found")

    media_type = mimetypes.guess_type(target)[0] or "application/octet-stream"
    return FileResponse(target, media_type=media_type)
