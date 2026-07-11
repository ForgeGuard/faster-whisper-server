# Changelog

Notable changes to **ForgeGuard Faster Whisper Server** are documented here. The
format is based on [Keep a Changelog](https://keepachangelog.com/) and the
project follows [Semantic Versioning](https://semver.org/). The `VERSION` file is
the single source of truth for the release version.

Per-PR detail is published automatically on each GitHub release page; this file
is the curated summary.

## [1.0.0]

First ForgeGuard release: a container-native, OpenAI-compatible speech-to-text
server built on faster-whisper, distributed as container images and a Helm chart
only. This release re-homes the project away from its upstream fork
(SYSTRAN/faster-whisper); the entries below summarize how it differs from that
starting point.

### Added
- **Orchestrator-ready startup contract.** The server binds and answers `GET /health`
  immediately while the model loads in a background task. `GET /health` reports
  `warming` → `healthy` with a `model_loaded` field; `GET /ready` returns 200 only
  once inference will succeed (503 + `Retry-After` while warming). Inference routes
  return 503 `model_warming` until ready. A permanently failed warmup exits the
  process non-zero (`WARMUP_ON_START=true` by default; set `false` for lazy load).
- **Models baked into the images at build time**, revision-pinned to canonical
  Systran CTranslate2 repositories (amd64 bakes `large-v3`, Jetson bakes `small`;
  both bake `tiny` for the smoke test). The image starts with zero network access.
  `MODEL_REVISION` overrides the pin; a custom `MODEL_SIZE` still downloads at runtime.
- **`GET /v1/models`** (OpenAI-style listing) and **`POST /v1/audio/translations`**
  (translate-to-English) endpoints.
- **Helm chart** (`charts/faster-whisper-server`) with startup/readiness probes on
  `/ready`, a liveness probe on `/health`, an existing-Secret API-key pattern, and
  `extraEnv` passthrough. Published as an OCI artifact to `ghcr.io/forgeguard/charts`.
- **Release pipeline** (`.github/workflows/release.yml`): builds and publishes the
  `-cu128`, unsuffixed-alias, and `-jetson` images, gated by a CPU smoke test that
  boots the image offline and asserts the health contract and a real transcription;
  packages and pushes the chart; creates the GitHub Release. A `validate_only`
  dispatch input pushes version tags only (no `:latest`, no Release) for pre-merge
  validation.
- **Dev container** (`.devcontainer/`) and a container-first `CONTRIBUTING.md`,
  including a "run tests inside the server image" fallback.
- Optional bearer-token authentication via `API_KEY` (constant-time comparison);
  `/health`, `/ready`, and the web console stay unauthenticated.
- Web console: a Vite + React + TypeScript + Tailwind speech-to-text interface at
  `/web` with file upload, mic recording, language/format selection, a model-warming
  banner, an inline "Enter API key" recovery flow, and transcript download
  (`.txt`/`.srt`/`.vtt`). Disable with `ENABLE_WEB_UI=false`.
- `MAX_UPLOAD_BYTES` guard (default 25 MB) rejecting oversized uploads with 413.

### Changed
- Container images install `faster-whisper` and pinned dependencies via `uv`
  from `pyproject.toml`/`uv.lock` (the single dependency source of truth). Ruff
  replaces black/isort/flake8. The image ships a `/app/.venv`.
- CI (`.github/workflows/ci.yml`) runs the unit suite and ruff on `main`; image
  build and smoke testing live solely in the release workflow.
- Transcription runs off the event loop (`run_in_threadpool`); `response_format=text`
  returns a `text/plain` body; `verbose_json` includes full segment fields and word
  timestamps.

### Removed
- **BREAKING:** the `/healthz` endpoint. Use `/health` (liveness) and `/ready`
  (readiness) instead; update any external monitors and container/orchestrator probes.
- **BREAKING:** the vendored `faster_whisper` library and all bare-metal / PyPI
  install support (`setup.py`, `requirements*.txt`, benchmark scripts, library
  tests). Distribution is container images + Helm chart only; the server depends on
  the PyPI `faster-whisper` package.

---

## Prior fork history

The following entry predates the re-homing above and is retained for provenance;
it described the project while it was still a fork of SYSTRAN/faster-whisper.

### [0.x] - 2026-07-04 (upstream fork)

First ForgeGuard server release atop the vendored library.

- Added a `server/` package (`config`, `auth`, `transcription`, `web`, `main`)
  served via `uvicorn server.main:app`, a Vite/React web console at `/web`, and a
  `MAX_UPLOAD_BYTES` upload guard.
- Pinned container runtime dependencies; both images run as a non-root user with
  the HF cache under `/home/appuser/.cache`. Jetson Portainer stack defaulted to
  `COMPUTE_TYPE=int8_float16`.
- Fixed transcription to run off the event loop; `response_format=text` returned a
  `text/plain` body and `verbose_json` emitted full segments and word timestamps.
