"""Model-mode admin API: list selectable sizes and switch the resident model.

Not part of the OpenAI surface (that stays fixed at ``GET /v1/models``). These
routes back the web console's model picker. Listing is safe to expose; the
switch mutates GPU state and is guarded by the same bearer auth as the rest of
the API (applied at include time in main.py).
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from server import model_manager

LOGGER = logging.getLogger("faster_whisper_api")

router = APIRouter()


class ActivateRequest(BaseModel):
    size: str


@router.get("/api/model/presets")
async def list_presets() -> dict:
    """Selectable model sizes plus which is active and which is resident."""
    return model_manager.presets_info()


@router.post("/api/model/activate")
async def activate_model(body: ActivateRequest) -> dict:
    """Switch the resident Whisper model to ``size`` (load/unload, persisted)."""
    try:
        # Blocking load/unload — keep it off the event loop.
        return await run_in_threadpool(model_manager.activate, body.size)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_model", "message": str(exc), "type": "invalid_request_error"},
        ) from exc
    except Exception as exc:  # noqa: BLE001 — a load failure is a 503, not a crash
        LOGGER.error("Model activation failed for '%s': %s", body.size, exc)
        raise HTTPException(
            status_code=503,
            detail={
                "error": "model_load_failed",
                "message": f"failed to load model '{body.size}': {exc}",
                "type": "server_error",
            },
        ) from exc
