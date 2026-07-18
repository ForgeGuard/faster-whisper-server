---
title: Health and readiness
description: The exact liveness and readiness contract, warmup and failure behavior, and probe wiring.
order: 50
status: stable
---

# Health and readiness

The server separates **liveness** (`/health`) from **readiness** (`/ready`) so
orchestrators can keep a warming container alive while withholding traffic until
the model can actually transcribe.

## The contract

The server binds `0.0.0.0:8000` and accepts connections immediately; the model
loads and warms in a background task (seconds on datacenter GPUs, longer on edge
devices).

| Endpoint | While warming | Ready | Failed warmup |
|---|---|---|---|
| `GET /health` (liveness) | `200` `{"status":"warming","model_loaded":false}` | `200` `{"status":"healthy","model_loaded":true,"device":…,"compute_type":…,"model":…}` | `503` `{"status":"failed","error":…}` (then the process exits non-zero) |
| `GET /ready` (readiness) | `503` `{"status":"warming"}` + `Retry-After: 10` | `200` `{"status":"ready"}` | `503` `{"status":"failed"}` + `Retry-After: 10` |
| `POST /v1/audio/transcriptions` | `503` `model_warming` + `Retry-After: 10` | normal | `503` `model_failed` (no `Retry-After`) |
| `GET /v1/models` | `200` (open during warmup) | `200` | `200` |

`/health` never sends a `Retry-After` header. `/ready` sends `Retry-After: 10` on
every non-ready response, and its body reports the current state
(`warming`, `failed`, or `uninitialized`).

## Failed warmup exits the process

A warmup that fails permanently (for example missing or unreadable weights) sets
the failed state and then exits the container with a non-zero code, so restart
policies and orchestrators see the failure instead of a healthy-looking server
that cannot transcribe. This is deliberate: a background exception would otherwise
be swallowed by the event loop.

## Lazy loading

Set `WARMUP_ON_START=false` to skip eager loading; the model then loads lazily on
the first inference request. In that mode the server reports `healthy` with
`model_loaded: false` until the first request triggers the load, and a
lazy-load failure does **not** wedge the readiness gate — the next request retries
the load.

## Inference during warmup

While the model is warming, inference returns `503` with error code
`model_warming` and `Retry-After: 10`. After a terminal failure it returns `503`
`model_failed` with no retry hint. The body carries both an OpenAI-shaped
`error` object and a `detail` object (`detail.error == "model_warming"`) so both
SDKs and the web console can react.

## Probe wiring

### Kubernetes (Helm chart)

- `startupProbe` → `/ready` (`periodSeconds: 5`, `failureThreshold: 60`)
- `readinessProbe` → `/ready` (`periodSeconds: 10`)
- `livenessProbe` → `/health` (`periodSeconds: 30`)

This keeps a warming pod alive (liveness on `/health`) while withholding traffic
(readiness on `/ready`) and tolerates a long cold load (startup on `/ready`).

### Docker / Compose

The images define a `HEALTHCHECK` that curls `/health`. The local Compose stack
overrides it with an HTTPS check and a 300 s start period to cover a cold model
load over TLS.

## Related

- [Observability and queues](./observability-and-queues.md) — live telemetry and
  admission behavior.
- [Model lifecycle](../architecture/model-lifecycle.md) — how warmup and readiness
  transitions work internally.
