---
title: Request lifecycle
description: What happens to a single transcription request from arrival to cleanup.
order: 61
status: stable
---

# Request lifecycle

This page traces a single `POST /v1/audio/transcriptions` (or `/translations`)
request from arrival to response, including exactly when the temporary audio file
is created and removed.

## Step by step

1. **Authentication.** When `API_KEY` is set, the bearer key is checked first
   (constant-time). A missing or invalid key returns `401` — before any
   readiness or model work.
2. **Readiness gate.** If the model is still warming, the request returns `503`
   `model_warming` with `Retry-After: 10`; if warmup failed terminally, `503`
   `model_failed`. If lazy loading is enabled and the model is not yet loaded, the
   request triggers the load.
3. **Admission gate.** The request enters the process-wide gate:
   - If `QUEUE_SIZE` requests are already waiting, it is rejected immediately with
     `503` `queue_full` (`Retry-After: 5`).
   - Otherwise it waits for a slot up to `QUEUE_TIMEOUT_S`; on timeout it returns
     `503` `queue_timeout` (`Retry-After: 10`). A client disconnect while waiting
     releases the slot.
4. **Spooling.** The upload is streamed to a temporary file in bounded 1 MB
   chunks. If cumulative bytes exceed `MAX_UPLOAD_BYTES`, the request returns
   `413` and the partial temp file is removed immediately.
5. **Validation.** `response_format` and `language` are validated; invalid values
   return `400` with an OpenAI-shaped error.
6. **Inference.** faster-whisper transcribes (or translates) the temp file in a
   threadpool — off the event loop so `/health` keeps responding — applying
   `BEAM_SIZE`, the VAD filter, `language`/`prompt`, and word timestamps if
   requested.
7. **Response.** The transcript is serialized in the requested format
   (`text`, `json`, `verbose_json`, `srt`, or `vtt`).
8. **Cleanup.** A `finally` step removes the temporary audio file. Cleanup runs on
   success, on inference errors, on `413`, on queue shedding, and on cancellation
   or disconnect — no request leaves audio on disk.

## Concurrency

`MAX_CONCURRENCY` (default `1`) sets how many requests run inference at once; the
rest wait in the bounded queue. The `active` and `waiting` counters are exposed
under `/system` → `activity`. See
[Observability and queues](../operations/observability-and-queues.md).

## Error envelope

Every error response carries an OpenAI-shaped body
`{"error": {"message", "type", "code"}}` alongside a `detail` object the web
console reads (for example `detail.error == "model_warming"`). See
[Common errors](../troubleshooting/common-errors.md) and the
[OpenAI-compatible API reference](../reference/openai-api.md).
