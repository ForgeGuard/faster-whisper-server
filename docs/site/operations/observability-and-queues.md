---
title: Observability and queues
description: The /system telemetry endpoint, GPU metrics, and the bounded admission queue.
order: 51
status: stable
---

# Observability and queues

The server exposes live telemetry at `/system` and protects the GPU with a
bounded admission queue. Both are visible in the web console monitor.

## The `/system` endpoint

`GET /system` is **open** (no authentication) and exposes no transcript content —
it is safe for the console monitor to poll before a key is entered. It returns:

| Field | Meaning |
|---|---|
| `version` | Server version |
| `state` | Model state (`warming`, `ready`, …) |
| `device`, `compute_type`, `model` | Active runtime and model |
| `gpu` | GPU telemetry, or `null` when no NVIDIA driver is present |
| `activity` | `{active, waiting}` request counters |
| `models` | Active model plus the selectable presets |

### GPU telemetry

When an NVIDIA driver is available, `gpu` reports best-effort utilization, memory
(`memory_total_bytes` and used), temperature, and power via NVML. On a host with
no driver (for example CPU-only), `gpu` is `null` and the console shows "GPU
telemetry unavailable" — this is expected, not an error.

## The admission queue

GPU transcription is serialized by default. Requests that arrive while a slot is
busy wait briefly in a bounded queue; the server sheds load with `503` responses
rather than building an unbounded backlog.

| Variable | Default | Effect |
|---|---|---|
| `MAX_CONCURRENCY` | `1` | Number of transcriptions running at once |
| `QUEUE_SIZE` | `32` | Maximum requests allowed to wait for a slot |
| `QUEUE_TIMEOUT_S` | `120` | Seconds a queued request waits before timing out |

Behavior:

- If the queue is already full (`QUEUE_SIZE` waiting), a new request is rejected
  immediately with `503`, error code `queue_full`, and `Retry-After: 5`.
- If a request waits longer than `QUEUE_TIMEOUT_S` for a slot, it is rejected with
  `503`, error code `queue_timeout`, and `Retry-After: 10`.
- A client that disconnects while waiting releases its place in the queue.

The `active` and `waiting` counters surfaced under `/system` → `activity` reflect
this gate in real time, and the console renders them as a "running / queued"
activity pill.

> Raising `MAX_CONCURRENCY` above `1` lets multiple transcriptions share the GPU.
> Size it to your GPU memory and latency goals; a single large model on a busy GPU
> usually runs best serialized.

## Logging

Application logs go to stdout at `INFO`. Transcript text is **not** logged unless
`LOG_INPUT_TEXT=true`; by default only lengths and timings are recorded (see
[Privacy and responsible use](../concepts/privacy-and-responsible-use.md)).

## Related

- [Health and readiness](./health-and-readiness.md) — liveness and readiness.
- [Request lifecycle](../architecture/request-lifecycle.md) — where the gate sits
  in a request.
