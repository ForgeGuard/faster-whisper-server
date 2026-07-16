# Security & data handling

Speech-to-text turns audio into text, and both the audio and the transcript are
frequently **sensitive personal data** (names, health details, financial
information, private conversations). The defaults here are conservative; loosen
them deliberately.

## Authentication

- `API_KEY` — bearer key for the OpenAI-compatible API (`/v1/...`) and the
  model-mode admin routes (`/api/model/*`). Empty disables auth (open server).
- `/health`, `/ready`, `/system`, and the web console (`/web/*`) never require
  auth: the first two are orchestrator probes, `/system` is non-PII telemetry
  for the console monitor, and the console must load before it holds a key.
- Clients send `Authorization: Bearer <key>` (the OpenAI convention). Comparison
  is constant-time; a non-ASCII token is a clean 401, not a 500.

## Health / readiness contract

- `/health` returns 200 as soon as the socket is open (including during model
  warmup); 503 only on a terminal load failure.
- `/ready` returns 200 only once the model can actually transcribe.
- Inference returns 503 `model_warming` while the model loads, and 503
  `queue_full` / `queue_timeout` when the admission gate sheds load.

## Privacy — transcripts and audio

- **Transcript text is never logged by default.** `LOG_INPUT_TEXT=false` (the
  default) keeps prompt and output text out of the logs; only lengths/timings
  are recorded. Enable it only for local debugging.
- **Uploaded audio is not persisted.** It is streamed to a temp file for the
  duration of the transcription and removed immediately afterward (including on
  client disconnect / cancellation). `PERSIST_AUDIO=false` is the default.
- `RETENTION_DAYS` (default `0` = keep nothing) is reserved for any future
  stored artifacts.
- Responses are OpenAI-shaped and expose no server filesystem paths.

## Uploads

- Bodies are read in bounded chunks and capped at `MAX_UPLOAD_BYTES` (default
  25 MB, matching OpenAI); an oversized upload is rejected with 413 up front and
  again mid-stream, so a lying `Content-Length` cannot exhaust memory or disk.
- Temp files are always cleaned up, even on cancellation.

## TLS (built-in HTTPS)

- `TLS_ENABLED=true` makes the server speak HTTPS directly (uvicorn SSL) — no
  reverse proxy. With no cert supplied a self-signed one is generated on first
  run (`server/tls.py`) and persisted under `<DATA_DIR>/tls` (key mode `0600`),
  so restarts reuse it. Generation is fully local/offline.
- The generated cert is for local/self-hosted testing; browsers warn it is
  untrusted. Point `TLS_CERT_FILE` / `TLS_KEY_FILE` at a real cert for anything
  public. In Kubernetes, terminate TLS at the ingress instead.

## Model-mode switching

- `POST /api/model/activate` loads/unloads the resident Whisper model and is
  **auth-guarded** (bearer key). Listing (`GET /api/model/presets`) is safe and
  open. The active choice is persisted to `<DATA_DIR>/active_model` and resumed
  on restart.

## Container hardening

- Images run as a non-root user (uid 1000). Only `<DATA_DIR>` (and `/tmp` / the
  HF cache) need to be writable. The Helm chart sets `runAsNonRoot`, `runAsUser`,
  an `fsGroup`, drops all capabilities, and disables privilege escalation;
  `readOnlyRootFilesystem` is compatible when the writable paths are mounts.

See [responsible-use.md](responsible-use.md) for the wider data-handling and
consent considerations around recording and transcribing people.
