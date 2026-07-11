"""OpenAI-compatible model listing.

Deliberately NOT gated on model readiness (no ``require_model_ready`` dependency):
it answers 200 while the model is still warming, so orchestrators and the release
smoke test can use it as a plain authentication check before ``/ready`` flips.
Authentication is applied a layer up, at include_router time in main.py.
"""

from fastapi import APIRouter

from server import config

router = APIRouter()

# Constant creation timestamp, mirroring OpenAI's example responses (the field is
# required by the schema but carries no real meaning for a self-hosted model).
_CREATED = 1686935002


@router.get("/v1/models")
async def list_models() -> dict:
    ids = ["whisper-1"]  # the model id OpenAI clients send by default
    if config.MODEL_SIZE not in ids:
        ids.append(config.MODEL_SIZE)  # the actually-configured Whisper model
    return {
        "object": "list",
        "data": [
            {"id": model_id, "object": "model", "created": _CREATED, "owned_by": "forgeguard"}
            for model_id in ids
        ],
    }
