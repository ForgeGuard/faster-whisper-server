# Changelog

Notable changes to **ForgeGuard Faster Whisper Server** are documented here. The
format is based on [Keep a Changelog](https://keepachangelog.com/) and the
project follows [Semantic Versioning](https://semver.org/). The `VERSION` file is
the single source of truth for the release version.

Per-PR detail is published automatically on each GitHub release page; this file
is the curated summary.

## [1.1.0]

### Added
- **Built-in HTTPS.** Set `TLS_ENABLED=true` and the server speaks HTTPS
  directly (uvicorn SSL) with no reverse proxy. When no cert is supplied it
  generates a self-signed one on first run (RSA 2048; SANs for the CN plus
  `localhost`/`127.0.0.1`/`::1`; ~10y validity), persists it under
  `<DATA_DIR>/tls` with the key at mode `0600`, and reuses it on restart.
  Configurable via `TLS_SELF_SIGNED`, `TLS_CERT_FILE`, `TLS_KEY_FILE`,
  `TLS_CN`, `TLS_SAN`.
- **Live GPU telemetry** on a new open `GET /system` endpoint: GPU
  utilization, VRAM, temperature, and power (best-effort via NVML), plus
  in-flight/queued request counts. The web console renders a compact,
  theme-matched GPU + activity monitor from it.
- **Runtime model switching.** Pick the resident Whisper size from the console
  (`tiny` … `large-v3`, `large-v3-turbo`, `distil-large-v3`) or via the
  auth-guarded `POST /api/model/activate`; the server loads/unloads to manage
  VRAM and persists the choice to `<DATA_DIR>/active_model`, resuming it on
  restart. `GET /api/model/presets` lists the catalog.
- **Whisper “turbo”** (`large-v3-turbo`) added to the model catalog. Bake extra
  sizes into an image at build time with `--build-arg EXTRA_MODELS="…"`.
- **Local single-GPU deployment**: `deploy/docker-compose.local.yml` brings the
  stack up with HTTPS, a reserved NVIDIA GPU, and an HTTPS healthcheck override.
- **Privacy controls for transcripts (PII).** `LOG_INPUT_TEXT=false` (default)
  keeps transcript text out of logs; `PERSIST_AUDIO=false` and `RETENTION_DAYS`
  document data handling. New `docs/security.md` and `docs/responsible-use.md`.
- **Container hardening**: the Helm chart now sets `runAsNonRoot`, `runAsUser`,
  an `fsGroup`, drops all capabilities, and disables privilege escalation.

### Changed
- The image entrypoint is now `python -m server`, a thin uvicorn wrapper that
  wires in TLS when enabled; behaviour is identical to the previous
  `uvicorn server.main:app` command when TLS is off.
- Web console: full product name as the app title with the section beneath it,
  browser-tab title `"<Section> · <App>"`, a model-size selector, the GPU/
  activity monitor, and a not-found view.

## [1.0.3]

### Fixed
- Word-level timestamps now work: the transcription endpoint accepts the
  OpenAI wire field name `timestamp_granularities[]`, which the console,
  README examples, and OpenAI SDKs all send.
- `GET /ready` no longer stays `503` forever when `WARMUP_ON_START=false`;
  lazy model loading marks readiness once the model is warm, so the chart's
  startup probe stops killing otherwise-healthy pods.
- `Authorization` headers containing non-ASCII bytes returned `500` instead
  of `401`.
- An unrecognized `language` parameter is now rejected with `400` before the
  upload is spooled, instead of a `500` from deep inside transcription.
- `DEVICE=auto` on a CPU-only host no longer crash-loops; the compute-type
  fallback now covers it.
- Uploaded audio spooled to a temp file is now cleaned up on write failure or
  client cancellation, not just on success.
- The web console's static file serving 404s missing hashed assets instead of
  serving `index.html` as `text/html`, which broke cache-busting after a
  redeploy.
- `verbose_json` no longer duplicates the word list once per segment and
  again at the top level; `srt`/`vtt` response formats are now supported
  server-side.
- Error responses use an OpenAI-shaped `error` envelope; `/health` reports
  the resolved device/compute-type/model.
- The Helm chart's `fasterWhisper.port` setting now actually changes the
  port the server listens on — previously the container command hardcoded
  `8000` regardless of the chart value.
- Web console: the health-poll banner no longer gets stuck on "failed"
  permanently after a transient error; a reverse-proxy path prefix like
  `/webtools` is now detected correctly; microphone recording no longer
  leaks an open stream on a double-click or a `MediaRecorder` failure;
  transcription requests are now cancellable instead of locking the UI on a
  hung server; segment timestamps no longer render as `0:60.0`.

## [1.0.2]

### Fixed
- Web console: accessing `/web` without a trailing slash now redirects to `/web/`,
  so the SPA's relative asset URLs resolve instead of 404-ing against the site root.
- Web console header title now reads "ForgeGuard Faster Whisper Server".

## [1.0.1]

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
