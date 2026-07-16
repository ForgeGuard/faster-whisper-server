"""Resident Whisper model management: load, unload, switch size, persist choice.

The server keeps a single Whisper model resident on the GPU. The operator can
switch which size is loaded at runtime (tiny → large-v3, distil-*) to trade
accuracy for VRAM/latency; switching unloads the current model before loading
the new one so a tight GPU never has to hold both at once. The active choice is
persisted to ``<DATA_DIR>/active_model`` and resumed on restart.

``get_model()`` is the single accessor shared by the warmup task and inference
requests (both may call it concurrently, so construction is serialized under a
lock). ``server.transcription.get_model`` delegates here — kept as a thin alias
so existing call sites and tests that patch it keep working.
"""

from __future__ import annotations

import gc
import logging
import os
import threading
from typing import Optional

from faster_whisper import WhisperModel

from server import config, model_status, provisioning

LOGGER = logging.getLogger("faster_whisper_api")

# Curated, selectable model sizes for the console picker. The resolver
# (server.provisioning) knows how to fetch each from the canonical Systran
# CTranslate2 repos; a size baked into the image loads with no network.
PRESETS: list[dict[str, str]] = [
    {"size": "tiny", "label": "Tiny", "params": "39M"},
    {"size": "base", "label": "Base", "params": "74M"},
    {"size": "small", "label": "Small", "params": "244M"},
    {"size": "medium", "label": "Medium", "params": "769M"},
    {"size": "large-v3", "label": "Large v3", "params": "1550M"},
    # Whisper "turbo": a pruned large-v3 decoder — near-large accuracy at a
    # fraction of the latency/VRAM. faster-whisper maps both "large-v3-turbo"
    # and the "turbo" alias to mobiuslabsgmbh/faster-whisper-large-v3-turbo.
    {"size": "large-v3-turbo", "label": "Large v3 Turbo", "params": "809M"},
    {"size": "distil-large-v3", "label": "Distil Large v3", "params": "756M"},
]

_KNOWN_SIZES = {p["size"] for p in PRESETS}

# Serializes model construction/teardown: @lru_cache-free so a switch can
# actually free and rebuild, and locked so warmup + an early request never
# double-allocate the GPU.
_lock = threading.Lock()
_model: Optional[WhisperModel] = None
_loaded_size: Optional[str] = None
# The size the operator wants resident (persisted choice or configured default),
# resolved lazily so tests importing this module don't touch the data dir.
_desired_size: Optional[str] = None


def _state_path() -> str:
    return os.path.join(config.DATA_DIR, "active_model")


def _read_persisted() -> Optional[str]:
    try:
        with open(_state_path(), encoding="utf-8") as handle:
            name = handle.read().strip()
        if name and is_valid_size(name):
            return name
    except OSError:
        pass
    return None


def _persist(size: str) -> None:
    try:
        os.makedirs(config.DATA_DIR, exist_ok=True)
        with open(_state_path(), "w", encoding="utf-8") as handle:
            handle.write(size)
    except OSError:  # best-effort: the choice still applies this run
        LOGGER.warning("could not persist active model '%s'", size)


def is_valid_size(size: str) -> bool:
    """A size is selectable if it's a known preset or the configured default."""
    return size in _KNOWN_SIZES or size == config.MODEL_SIZE


def active_model() -> str:
    """The size the server intends to serve (persisted choice, else default)."""
    global _desired_size
    if _desired_size is None:
        _desired_size = _read_persisted() or config.MODEL_SIZE
    return _desired_size


def loaded_size() -> Optional[str]:
    """The size actually resident on the device right now (None until warmed)."""
    return _loaded_size


def presets_info() -> dict:
    """List of selectable sizes with active/loaded flags for the UI/`/system`."""
    active = active_model()
    presets = list(PRESETS)
    # Surface a configured custom default that isn't in the curated list.
    if config.MODEL_SIZE not in _KNOWN_SIZES:
        presets = [{"size": config.MODEL_SIZE, "label": config.MODEL_SIZE, "params": ""}, *presets]
    return {
        "active": active,
        "loaded": _loaded_size,
        "presets": [
            {**p, "is_active": p["size"] == active, "is_loaded": p["size"] == _loaded_size}
            for p in presets
        ],
    }


def _build(size: str) -> WhisperModel:
    resolved = provisioning.resolve_model(size, config.MODEL_DIR, config.MODEL_REVISION)
    LOGGER.info(
        "Loading WhisperModel(model=%s, source=%s, revision=%s, device=%s, compute_type=%s)",
        resolved.model_path_or_id,
        resolved.source,
        resolved.revision,
        config.DEVICE,
        config.COMPUTE_TYPE,
    )
    return WhisperModel(
        resolved.model_path_or_id,
        device=config.DEVICE,
        compute_type=config.COMPUTE_TYPE,
        revision=resolved.revision,
    )


def get_model() -> WhisperModel:
    """Thread-safe accessor for the resident model, loading it on demand.

    Loads (or reloads, after a size switch) under the lock so the warmup task and
    a concurrent lazy request never both construct a model. A failed load raises
    and leaves state untouched, so the next call simply retries — which is why a
    lazy-load failure must NOT flip model_status to FAILED (reserved for a
    terminal warmup failure in main.py).
    """
    global _model, _loaded_size
    want = active_model()
    with _lock:
        if _model is None or _loaded_size != want:
            model = _build(want)
            _model = model
            _loaded_size = want
        model = _model
    model_status.set_ready(config.DEVICE, config.COMPUTE_TYPE, want)
    return model


def _unload_locked() -> None:
    """Free the resident model. Caller must hold ``_lock``."""
    global _model, _loaded_size
    if _model is not None:
        LOGGER.info("Unloading model '%s'", _loaded_size)
        _model = None
        _loaded_size = None
        gc.collect()  # CTranslate2 frees device memory on deallocation


def activate(size: str) -> dict:
    """Switch the resident model to ``size``, persist the choice, and reload.

    Unloads the current model first so a switch on a tight GPU never holds both
    at once. Raises ValueError for an unknown size; on a load failure the server
    is left with no resident model (model_status set FAILED) and the caller
    surfaces a 503.
    """
    global _desired_size
    if not is_valid_size(size):
        raise ValueError(f"unknown model size '{size}'")
    with _lock:
        _unload_locked()
        _desired_size = size
        model_status.set_warming()
    _persist(size)
    # Build outside the status lock but under the model lock via get_model, which
    # sets READY on success.
    try:
        get_model()
    except Exception as exc:  # noqa: BLE001 — surface the failure to the caller
        model_status.set_failed(str(exc))
        raise
    return presets_info()


def reset() -> None:
    """Drop resident state (test isolation)."""
    global _model, _loaded_size, _desired_size
    with _lock:
        _model = None
        _loaded_size = None
        _desired_size = None
