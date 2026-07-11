"""FastAPI application entrypoint: ``uvicorn server.main:app``."""

import asyncio
import contextlib
import logging
import os
import sys
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from server import config, model_status, models, transcription, web
from server.auth import require_api_key
from server.model_status import ModelStatus
from server.version import __version__

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("faster_whisper_api")


async def _warmup(app: FastAPI) -> None:
    """Load the Whisper model in the background so the socket serves immediately.

    A permanent warmup failure exits the process non-zero via ``os._exit``: a
    plain ``raise`` inside a background task is swallowed by the event loop, and
    ``sys.exit`` here historically produced an exit-0 silent restart loop (the
    orchestrator saw a clean exit and kept restarting). ``os._exit`` after
    flushing guarantees the non-zero code the managed stack needs to surface the
    failure. Note a *lazy*-load failure (WARMUP_ON_START disabled) does NOT set
    FAILED — get_model retries via its uncached exception, so wedging the
    readiness gate would be wrong.
    """
    from server.transcription import get_model  # import at call time so tests can patch

    try:
        # get_model blocks in CTranslate2/C++ during load — never call it inline
        # on the event loop or /health stalls during the exact window it exists for.
        await run_in_threadpool(get_model)
    except Exception as exc:  # noqa: BLE001 — any failure here is terminal
        model_status.set_failed(str(exc))
        LOGGER.error("Failed to load model, exiting: %s", exc)
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)
    model_status.set_ready(config.DEVICE, config.COMPUTE_TYPE, config.MODEL_SIZE)
    LOGGER.info(
        "Model warmed up: %s on %s (%s)",
        config.MODEL_SIZE,
        config.DEVICE,
        config.COMPUTE_TYPE,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start serving immediately; model warmup runs as a background task."""
    if config.WARMUP_ON_START:  # attribute access so tests can monkeypatch it
        model_status.set_warming()
        # Held on app.state so the task isn't garbage-collected mid-flight.
        app.state.warmup_task = asyncio.create_task(_warmup(app))
        LOGGER.info("Server accepting connections; model warming in background")
    else:
        LOGGER.info("WARMUP_ON_START disabled; model will load on first request")
    yield
    task = getattr(app.state, "warmup_task", None)
    if task is not None and not task.done():
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title="ForgeGuard Faster Whisper Server",
    description=(
        "OpenAI-compatible speech-to-text API built on faster-whisper, "
        "with an optional web console."
    ),
    version=__version__,
    lifespan=lifespan,
)

# Auth is applied at include time. These router-level dependencies run BEFORE the
# routers' own require_model_ready dependency, so a missing/invalid key returns
# 401 even while the model is warming (401 beats the warming 503). /health,
# /ready and /web/* are registered without it and stay open.
_auth = [Depends(require_api_key)]
app.include_router(transcription.router, dependencies=_auth)
app.include_router(models.router, dependencies=_auth)
if config.ENABLE_WEB_UI:
    app.include_router(web.router)


@app.get("/health")
async def health_check():
    """Liveness: 200 as soon as the socket is open; 503 only for a failed warmup."""
    status = model_status.get_status()
    if status is ModelStatus.FAILED:
        return JSONResponse(
            status_code=503,
            content={"status": "failed", "error": model_status.get_error()},
        )
    if status is ModelStatus.WARMING:
        return {"status": "warming", "model_loaded": False}
    return {"status": "healthy", "model_loaded": status is ModelStatus.READY}


@app.get("/ready")
async def readiness_check():
    """Readiness: 200 only once the model is warmed and inference will succeed."""
    status = model_status.get_status()
    if status is ModelStatus.READY:
        return {"status": "ready"}
    return JSONResponse(
        status_code=503,
        content={"status": status.value},
        headers={"Retry-After": "10"},
    )
