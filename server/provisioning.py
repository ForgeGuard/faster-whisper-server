"""Model resolution and integrity pinning — shared by runtime and build time.

This is the single source of truth for *where* a model comes from and *which
revision* is trusted. It is imported both by ``transcription.get_model`` at
runtime and by ``docker/scripts/download_model.py`` when baking weights into the
image, so the pin table can never drift between the two.

Philosophy (mirrors the kokoro-server model provisioning):
- Default weights are baked into each image at build time from the canonical
  Systran CTranslate2 repos, pinned to a specific commit revision.
- The pin is applied *only* when the model resolves to a canonical Systran repo
  and the operator has not supplied an override. A custom ``MODEL_SIZE`` (any
  non-Systran repo id) or an explicit ``MODEL_REVISION`` bypasses the built-in
  pins — we never silently pin weights we do not vet.
"""

import os
from dataclasses import dataclass
from typing import Optional

# Canonical Systran-owned CTranslate2 repos (a curated subset of
# ``faster_whisper.utils._MODELS`` — vendored here so we do not depend on a
# private attribute of the library, and so non-Systran community repos such as
# ``distil-large-v3.5``/``large-v3-turbo`` are deliberately excluded from pinning).
_CANONICAL_REPOS = {
    "tiny": "Systran/faster-whisper-tiny",
    "tiny.en": "Systran/faster-whisper-tiny.en",
    "base": "Systran/faster-whisper-base",
    "base.en": "Systran/faster-whisper-base.en",
    "small": "Systran/faster-whisper-small",
    "small.en": "Systran/faster-whisper-small.en",
    "medium": "Systran/faster-whisper-medium",
    "medium.en": "Systran/faster-whisper-medium.en",
    "large-v1": "Systran/faster-whisper-large-v1",
    "large-v2": "Systran/faster-whisper-large-v2",
    "large-v3": "Systran/faster-whisper-large-v3",
    "large": "Systran/faster-whisper-large-v3",
    "distil-large-v2": "Systran/faster-distil-whisper-large-v2",
    "distil-medium.en": "Systran/faster-distil-whisper-medium.en",
    "distil-small.en": "Systran/faster-distil-whisper-small.en",
    "distil-large-v3": "Systran/faster-distil-whisper-large-v3",
}

# Pinned commit revisions for the repos this project bakes and/or tests. Only
# these get an automatic pin; other canonical repos download at their branch
# HEAD unless the operator passes MODEL_REVISION.
PINNED_REVISIONS = {
    "Systran/faster-whisper-large-v3": "edaa852ec7e145841d8ffdb056a99866b5f0a478",  # amd64 image default
    "Systran/faster-whisper-small": "536b0662742c02347bc0e980a01041f333bce120",  # jetson image default
    "Systran/faster-whisper-tiny": "d90ca5fe260221311c53c58e660288d3deb8d356",  # CI / smoke fixture
}


def canonical_repo(model_size_or_id: str) -> Optional[str]:
    """Systran repo for a size alias, the id itself if it is a pinned repo, else None."""
    if model_size_or_id in _CANONICAL_REPOS:
        return _CANONICAL_REPOS[model_size_or_id]
    if model_size_or_id in PINNED_REVISIONS:
        return model_size_or_id
    return None


def resolve_revision(model_size_or_id: str, override: Optional[str] = None) -> Optional[str]:
    """Which git revision to download: override wins, else the built-in pin, else None."""
    if override:
        return override
    repo = canonical_repo(model_size_or_id)
    if repo is not None:
        return PINNED_REVISIONS.get(repo)
    return None


@dataclass(frozen=True)
class ResolvedModel:
    model_path_or_id: str  # a local baked dir, or a size alias / repo id for hub download
    revision: Optional[str]  # None for a local dir (revision is irrelevant on disk)
    source: str  # "baked" | "hub"


def resolve_model(
    model_size: str,
    model_dir: Optional[str],
    revision_override: Optional[str] = None,
) -> ResolvedModel:
    """Prefer a baked local model dir; fall back to a (revision-pinned) hub download.

    A baked dir counts only when it actually contains ``model.bin`` — an empty or
    partial ``<model_dir>/<size>`` directory (e.g. a volume mounted over it) must
    never be handed to ``WhisperModel``, which would raise a confusing CTranslate2
    error. In that case we fall through to the hub path.
    """
    if model_dir:
        baked = os.path.join(model_dir, model_size)
        if os.path.isfile(os.path.join(baked, "model.bin")):
            return ResolvedModel(model_path_or_id=baked, revision=None, source="baked")
    return ResolvedModel(
        model_path_or_id=model_size,
        revision=resolve_revision(model_size, revision_override),
        source="hub",
    )
