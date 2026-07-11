"""ForgeGuard Faster Whisper Server — an OpenAI-compatible STT API and web console.

A small FastAPI application built on the ``faster-whisper`` library. Its version
(see :mod:`server.version`) is sourced from the repository ``VERSION`` file.
"""

from server.version import __version__

__all__ = ["__version__"]
