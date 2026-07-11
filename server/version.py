"""Server release version, sourced from the repository/image ``VERSION`` file.

``VERSION`` at the repo root is the single source of truth (see also
``pyproject.toml`` and the Helm chart, kept in sync by ``scripts/update_version.py``).
This tracks the ForgeGuard server/image release, not the underlying
faster-whisper library version.
"""

from pathlib import Path


def _read_version() -> str:
    # In the container the app lives at /app with VERSION copied alongside it; in
    # a source checkout VERSION sits at the repo root (one level above this package).
    candidates = (
        Path("/app/VERSION"),
        Path(__file__).resolve().parent.parent / "VERSION",
    )
    for candidate in candidates:
        try:
            text = candidate.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if text:
            return text
    return "0.0.0"


__version__ = _read_version()
