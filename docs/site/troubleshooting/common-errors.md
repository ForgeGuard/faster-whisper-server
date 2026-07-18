---
title: Common errors
description: Diagnose and resolve the errors you are most likely to hit.
order: 80
status: stable
---

# Common errors

## `503` with `model_warming`

The model is still loading. This is expected right after start. Poll `/ready`
until it returns `200`, then retry. The response carries `Retry-After: 10`. See
[Health and readiness](../operations/health-and-readiness.md).

## `503` with `model_failed`

Model warmup failed terminally (for example missing or unreadable weights). With
eager warmup the container also exits non-zero, so check the container logs for
the underlying load error. Common causes: a volume mounted over `/app/models`
shadowing the baked weights, or a bad `MODEL_SIZE` / `MODEL_REVISION`. See
[Model provisioning](./model-provisioning.md).

## `503` with `queue_full` or `queue_timeout`

The admission gate shed load. `queue_full` means `QUEUE_SIZE` requests were
already waiting (`Retry-After: 5`); `queue_timeout` means a request waited longer
than `QUEUE_TIMEOUT_S` for a slot (`Retry-After: 10`). Reduce request concurrency,
raise `MAX_CONCURRENCY` if the GPU has headroom, or increase `QUEUE_SIZE` /
`QUEUE_TIMEOUT_S`. See [Observability and queues](../operations/observability-and-queues.md).

## `401` Invalid API key

`API_KEY` is set on the server and the request is missing or sending the wrong
`Authorization: Bearer <key>` header. Confirm the key, and remember `/health`,
`/ready`, `/system`, and `/web/*` are always open. In the web console, enter the
key in settings.

## `413` Uploaded file is too large

The body exceeds `MAX_UPLOAD_BYTES` (default 25 MB). Send a smaller file, or raise
`MAX_UPLOAD_BYTES` (set `0` to disable the cap — not recommended on an exposed
deployment).

## `400` Unsupported response_format / Unsupported language

`response_format` must be one of `text`, `json`, `verbose_json`, `srt`, `vtt`.
`language` must be a supported Whisper language code, or omitted to auto-detect.

## GPU telemetry unavailable

`/system` reports `gpu: null` and the console shows "GPU telemetry unavailable"
when there is no NVIDIA driver (for example a CPU-only host). This is expected and
does not affect transcription. On a GPU host, confirm the NVIDIA Container Toolkit
is installed and the container was started with GPU access.

## Browser warns the TLS certificate is untrusted

When using built-in self-signed TLS, browsers warn because the certificate is not
publicly trusted — expected for local use. Supply a real certificate via
`TLS_CERT_FILE` / `TLS_KEY_FILE`, or terminate TLS at an ingress. See
[Security hardening](../operations/security-hardening.md).

## Microphone recording is disabled in the console

The console enables mic capture only in a secure context (HTTPS or
`http://localhost`). File upload works on any origin. Serve the console over TLS or
access it via `localhost` to record.

## Slow transcription / high latency

Latency scales with model size and hardware. On CPU, throughput is much lower
(`int8`). On Jetson, stay within the memory budget. Consider a smaller or
distilled model — see [Model selection](../concepts/model-selection.md) and
[Hardware profiles](../deployment/hardware-profiles.md).
