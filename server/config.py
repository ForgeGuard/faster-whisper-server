"""Runtime configuration read from environment variables."""

import os


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


# Model / inference
MODEL_SIZE = os.getenv("MODEL_SIZE", "large-v3")
DEVICE = os.getenv("DEVICE", "cuda").strip().lower()
# COMPUTE_TYPE default is device-dependent: float16 on CUDA, int8 on CPU
# (CTranslate2 cannot run float16 on CPU), and "default" for anything else
# (e.g. DEVICE=auto — CTranslate2 then picks the best supported type for
# whatever device it lands on). An explicit COMPUTE_TYPE env wins verbatim.
_COMPUTE_TYPE_ENV = os.getenv("COMPUTE_TYPE")
if _COMPUTE_TYPE_ENV:
    COMPUTE_TYPE = _COMPUTE_TYPE_ENV
elif DEVICE == "cuda":
    COMPUTE_TYPE = "float16"
elif DEVICE == "cpu":
    COMPUTE_TYPE = "int8"
else:
    COMPUTE_TYPE = "default"
BEAM_SIZE = int(os.getenv("BEAM_SIZE", "5"))
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE") or None
ENABLE_VAD_FILTER = _as_bool(os.getenv("ENABLE_VAD_FILTER", "true"))

# Non-blocking startup: warm the model in a background task at boot so the socket
# serves /health immediately (the managed-stack contract). Set false to skip
# eager loading and fall back to lazy load on the first request.
WARMUP_ON_START = _as_bool(os.getenv("WARMUP_ON_START", "true"))

# Directory holding models baked into the image at build time, as
# ``<MODEL_DIR>/<MODEL_SIZE>``. Deliberately outside HF_HOME so a cache volume
# mounted there cannot shadow the baked weights. Empty string disables the baked
# lookup (forces the hub download path — used by the dev/test environment).
MODEL_DIR = os.getenv("MODEL_DIR", "/app/models")

# Optional Hugging Face git revision override for hub downloads. When set it also
# bypasses the built-in pin table in server.provisioning (we only auto-pin the
# canonical Systran revisions we vet; an explicit override is the operator's call).
MODEL_REVISION = os.getenv("MODEL_REVISION") or None

# Auth — when unset, the API is open (auth disabled).
API_KEY = os.getenv("API_KEY") or None

# Upload guard — reject bodies larger than this (bytes). Default 25 MB, matching
# the OpenAI audio endpoint limit. Set MAX_UPLOAD_BYTES=0 to disable the cap.
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))

# Web console static assets (built by the Docker node stage into this dir).
WEBUI_DIST_DIR = os.getenv("WEBUI_DIST_DIR", "/app/webui_dist")
ENABLE_WEB_UI = _as_bool(os.getenv("ENABLE_WEB_UI", "true"))
