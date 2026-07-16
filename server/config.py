"""Runtime configuration read from environment variables."""

import os


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_list(value: str) -> list[str]:
    """Split a comma-separated env value into a trimmed, non-empty list."""
    return [item.strip() for item in value.split(",") if item.strip()]


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

# Persistent, writable state directory. Holds the generated TLS cert/key
# (<DATA_DIR>/tls) and the persisted active model choice (<DATA_DIR>/active_model)
# so both survive a restart. In the container this is a mounted volume; on a dev
# box it defaults to ./data under the working dir.
DATA_DIR = os.getenv("DATA_DIR", "/data")

# --- Concurrency / admission ------------------------------------------------
# GPU transcription is serialized by default (one active request); additional
# requests wait briefly in a bounded queue, and the server sheds load with 503s
# rather than building an unbounded backlog. Drives the /system activity meter.
MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "1"))
QUEUE_SIZE = int(os.getenv("QUEUE_SIZE", "32"))
QUEUE_TIMEOUT_S = float(os.getenv("QUEUE_TIMEOUT_S", "120"))

# --- Privacy / responsible use ----------------------------------------------
# Transcripts are sensitive PII. By default the server never writes transcript
# text (input prompts or output) to its logs; flip LOG_INPUT_TEXT on only for
# local debugging. PERSIST_AUDIO keeps uploaded audio off disk beyond the
# transcription temp file; RETENTION_DAYS is reserved for any future stored
# artifacts (0 = keep forever).
LOG_INPUT_TEXT = _as_bool(os.getenv("LOG_INPUT_TEXT", "false"))
PERSIST_AUDIO = _as_bool(os.getenv("PERSIST_AUDIO", "false"))
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "0"))

# --- TLS --------------------------------------------------------------------
# When enabled the server speaks HTTPS directly (uvicorn SSL). If no cert is
# provided a self-signed one is generated on first run and persisted under
# <DATA_DIR>/tls so restarts reuse it — no reverse proxy or manual openssl.
# Point TLS_CERT_FILE / TLS_KEY_FILE at a real cert for anything public.
TLS_ENABLED = _as_bool(os.getenv("TLS_ENABLED", "false"))
TLS_SELF_SIGNED = _as_bool(os.getenv("TLS_SELF_SIGNED", "true"))
TLS_CERT_FILE = os.getenv("TLS_CERT_FILE") or os.path.join(DATA_DIR, "tls", "cert.pem")
TLS_KEY_FILE = os.getenv("TLS_KEY_FILE") or os.path.join(DATA_DIR, "tls", "key.pem")
TLS_CN = os.getenv("TLS_CN", "localhost")
TLS_SAN = _as_list(os.getenv("TLS_SAN", ""))

# Server bind address, read by the ``python -m server`` entrypoint (the uvicorn
# CLI path in Helm passes --host/--port instead).
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
