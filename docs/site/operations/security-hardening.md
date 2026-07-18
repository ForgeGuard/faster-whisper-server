---
title: Security hardening
description: Authentication, TLS, upload limits, temporary-file handling, and container hardening.
order: 52
status: stable
---

# Security hardening

This server handles potentially sensitive audio and transcripts. The defaults are
conservative; loosen them deliberately. This page covers the concrete controls;
for the wider consent and data-protection context see
[Privacy and responsible use](../concepts/privacy-and-responsible-use.md).

## Authentication

- `API_KEY` is the bearer key for the OpenAI-compatible API (`/v1/...`) and the
  model-admin routes (`/api/model/*`). Unset means auth is disabled (open server).
- `/health`, `/ready`, `/system`, and the web console (`/web/*`) never require
  auth: the first two are orchestrator probes, `/system` is non-PII telemetry for
  the console monitor, and the console must load before it can hold a key.
- Clients send `Authorization: Bearer <key>`. Comparison is constant-time, and a
  non-ASCII token returns a clean `401`, not a `500`.

See the full route/auth table in
[Configuration overview](../configuration/overview.md).

## Uploads

- Request bodies are read in bounded 1 MB chunks and capped at `MAX_UPLOAD_BYTES`
  (default 25 MB, matching OpenAI). An oversized upload is rejected with `413` both
  up front (from the declared size) and mid-stream (from bytes actually read), so a
  lying or missing `Content-Length` cannot exhaust memory or disk.
- Set `MAX_UPLOAD_BYTES=0` to disable the cap (not recommended on an exposed
  deployment).

## Temporary audio files

- Each upload is streamed to a per-request temporary file for the duration of the
  transcription and removed immediately afterward.
- Cleanup runs on **every** exit path: success, inference error, `413` rejection,
  queue shedding, and client cancellation or disconnect. There is no code path
  that leaves audio on disk after a request.
- `PERSIST_AUDIO` and `RETENTION_DAYS` are reserved and currently have no effect —
  do not rely on them to change this behavior.

## Transcript privacy

- Transcript text is **never logged by default**. `LOG_INPUT_TEXT=false` keeps
  prompt and output text out of the logs; only lengths and timings are recorded.
  Enable it only for local debugging.
- Responses are OpenAI-shaped and expose no server filesystem paths.

## TLS (built-in HTTPS)

`TLS_ENABLED=true` makes the `python -m server` entrypoint speak HTTPS directly
(uvicorn SSL) — no reverse proxy. With no certificate supplied and
`TLS_SELF_SIGNED=true`, a self-signed certificate is generated on first run and
persisted under `<DATA_DIR>/tls`:

- RSA 2048-bit key, SHA-256 signature, ~10-year validity.
- SANs always include the CN, `localhost`, `127.0.0.1`, and `::1`, plus anything
  in `TLS_SAN`.
- The private key is written first at file mode `0600`; restarts reuse the
  persisted pair.
- Generation is fully local and offline.

The generated certificate is for local/self-hosted use — **browsers will warn that
it is untrusted, and it is not publicly trusted**. For anything public, either
point `TLS_CERT_FILE` / `TLS_KEY_FILE` at a real certificate, or terminate TLS at
an ingress/reverse proxy and run the server behind it. If `TLS_ENABLED=true` but
no certificate exists and `TLS_SELF_SIGNED=false`, the entrypoint exits with an
error rather than serving plaintext.

> The Helm chart runs `uvicorn` directly and does not wire the built-in TLS path;
> terminate TLS at the ingress in Kubernetes.

## Container hardening

- Images run as a non-root user (uid 1000). Only `DATA_DIR` (and `/tmp` / the
  Hugging Face cache) need to be writable.
- The Helm chart sets `runAsNonRoot`, `runAsUser: 1000`, an `fsGroup`, drops all
  capabilities, and disables privilege escalation. `readOnlyRootFilesystem` is
  available (commented out) and is compatible when the writable paths are mounts.

## A minimum bar before exposing a deployment

Beyond a single trusted operator: require an `API_KEY`, serve over TLS (built-in
or terminated at an ingress), keep `LOG_INPUT_TEXT=false`, keep the upload cap on,
and publish an acceptable-use / abuse-contact process.
