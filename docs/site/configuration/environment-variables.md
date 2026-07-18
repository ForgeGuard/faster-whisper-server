---
title: Environment variables
description: The complete list of environment variables, their defaults, and effects.
order: 31
status: stable
---

# Environment variables

Every setting is a plain (unprefixed) environment variable read once at startup.
The `.env.example` file at the repository root carries the same list with inline
comments.

## Server

| Variable | Default | Purpose |
|---|---|---|
| `HOST` | `0.0.0.0` | Bind address (used by the `python -m server` entrypoint) |
| `PORT` | `8000` | Bind port (used by the `python -m server` entrypoint) |
| `DATA_DIR` | `/data` | Writable state dir: TLS cert/key (`<DATA_DIR>/tls`) and the persisted active model (`<DATA_DIR>/active_model`) |
| `UVICORN_ROOT_PATH` | *(unset)* | Path prefix when served behind a reverse proxy (e.g. `/whisper`) |

> The Helm chart launches `uvicorn ... --host 0.0.0.0 --port 8000` directly, so
> `HOST`/`PORT` apply to container runs via the default entrypoint, not to the
> chart.

## Model and inference

| Variable | Default | Purpose |
|---|---|---|
| `MODEL_SIZE` | `large-v3` (x86 image); `small` (Jetson image) | Whisper size alias or a CTranslate2 repo id to load |
| `DEVICE` | `cuda` | `cuda`, `cpu`, or `auto` (trimmed and lowercased) |
| `COMPUTE_TYPE` | device-dependent | Explicit value wins; otherwise `float16` on `cuda`, `int8` on `cpu`, `default` on anything else |
| `BEAM_SIZE` | `5` | Beam-search width |
| `DEFAULT_LANGUAGE` | *(auto)* | Fallback source language when a request omits `language`; empty means auto-detect |
| `ENABLE_VAD_FILTER` | `true` | Skip non-speech with voice-activity detection |
| `MODEL_DIR` | `/app/models` | Baked-model dir (`<MODEL_DIR>/<MODEL_SIZE>`); empty string forces the Hugging Face download path |
| `MODEL_REVISION` | *(unset)* | Hugging Face git revision override for hub downloads; bypasses the built-in pin table |

> `COMPUTE_TYPE` is **not** a fixed default. CTranslate2 cannot run `float16` on
> CPU, so the server chooses `int8` when `DEVICE=cpu`. Setting `COMPUTE_TYPE`
> explicitly always wins, verbatim.

## Startup and concurrency

| Variable | Default | Purpose |
|---|---|---|
| `WARMUP_ON_START` | `true` | Eagerly load and warm the model in a background task at boot; `false` loads lazily on the first request |
| `MAX_CONCURRENCY` | `1` | Active transcriptions at once (feeds the `/system` activity meter) |
| `QUEUE_SIZE` | `32` | Maximum requests allowed to wait for a slot before shedding with `503 queue_full` |
| `QUEUE_TIMEOUT_S` | `120` | Seconds a queued request waits for a slot before `503 queue_timeout` |

## Security

| Variable | Default | Purpose |
|---|---|---|
| `API_KEY` | *(unset)* | When set, protected routes require `Authorization: Bearer <key>`; unset leaves the API open |
| `MAX_UPLOAD_BYTES` | `26214400` | Reject uploads larger than this (25 MB); `0` disables the cap |

## Privacy

| Variable | Default | Purpose |
|---|---|---|
| `LOG_INPUT_TEXT` | `false` | Log transcript text — **keep off**; transcripts are sensitive PII. Off logs only lengths and timings |
| `PERSIST_AUDIO` | `false` | **Reserved / not enforced.** No code path persists audio; uploads always use a per-request temp file that is deleted afterward |
| `RETENTION_DAYS` | `0` | **Reserved / not enforced.** Placeholder for future stored-artifact retention |

> `PERSIST_AUDIO` and `RETENTION_DAYS` are declared but currently have **no runtime
> effect** — see [Privacy and responsible use](../concepts/privacy-and-responsible-use.md).

## Web console

| Variable | Default | Purpose |
|---|---|---|
| `ENABLE_WEB_UI` | `true` | Serve the web console at `/web` |
| `WEBUI_DIST_DIR` | `/app/webui_dist` | Directory of the built console assets (populated by the image build) |

## TLS

| Variable | Default | Purpose |
|---|---|---|
| `TLS_ENABLED` | `false` | Serve HTTPS directly via uvicorn SSL (honored by the `python -m server` entrypoint) |
| `TLS_SELF_SIGNED` | `true` | Auto-generate a self-signed cert on first run if none is supplied |
| `TLS_CERT_FILE` | `<DATA_DIR>/tls/cert.pem` | Certificate path; set to supply your own |
| `TLS_KEY_FILE` | `<DATA_DIR>/tls/key.pem` | Private key path; set to supply your own |
| `TLS_CN` | `localhost` | Common name of the generated cert |
| `TLS_SAN` | *(none)* | Extra Subject Alternative Names, comma-separated |

See [Security hardening](../operations/security-hardening.md) for how the
generated certificate is produced and when to replace it.

## Related

- [Configuration overview](./overview.md) — the configuration model and auth
  boundary.
- [Configuration reference](../reference/configuration.md) — the same values in a
  compact, tooling-friendly form.
