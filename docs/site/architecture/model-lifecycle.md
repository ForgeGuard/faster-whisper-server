---
title: Model lifecycle
description: Model loading, background warmup, readiness transitions, runtime switching, and persistence.
order: 62
status: stable
---

# Model lifecycle

The server holds a single resident Whisper model. This page describes how it is
loaded, how readiness transitions, how the model is switched at runtime, and what
persists.

## States

The model status moves through four states:

- **uninitialized** — process started, no model loaded yet.
- **warming** — the model is loading in the background.
- **ready** — the model is loaded and inference will succeed.
- **failed** — a terminal load failure.

`/health` and `/ready` report these states; see
[Health and readiness](../operations/health-and-readiness.md).

## Startup and warmup

With `WARMUP_ON_START=true` (the default), the application starts serving
immediately and launches a background task that loads the model off the event
loop. When it succeeds, readiness flips to **ready** with the active model's
device, compute type, and size. If it fails terminally, the state is set to
**failed** and the process exits non-zero so orchestrators surface the failure.

With `WARMUP_ON_START=false`, no eager load happens; the model loads lazily on the
first inference request. A lazy-load failure does not set **failed** — the next
request retries.

## Provisioning

At load time the model is resolved from one of two sources:

- **Baked** — if `<MODEL_DIR>/<size>/model.bin` exists, that copy is used with no
  download.
- **Hugging Face** — otherwise the model is downloaded. Canonical Systran
  repositories are pinned to a vetted git revision; a custom repo id or an explicit
  `MODEL_REVISION` bypasses that pin.

See [Model selection](../concepts/model-selection.md) and
[Model provisioning](../troubleshooting/model-provisioning.md).

## Runtime switching

`POST /api/model/activate` (authenticated) switches the resident model without a
restart:

1. Validate the requested size against the presets (or the configured
   `MODEL_SIZE`).
2. Unload the current model and free GPU memory; set state to **warming**.
3. Persist the choice to `<DATA_DIR>/active_model`.
4. Load the new model (downloading it if it is not baked in) and set **ready**; a
   load failure sets **failed** and returns `503`.

Loads and switches are serialized, so concurrent activations do not race. See the
[Model admin API reference](../reference/model-admin-api.md).

## Persistence and resume

The active-model choice is written to `<DATA_DIR>/active_model` and resumed on the
next start, ahead of the configured `MODEL_SIZE` default. Mount `DATA_DIR` on a
durable volume so the selection survives restarts and upgrades.

## Related

- [Request lifecycle](./request-lifecycle.md)
- [Hardware profiles](../deployment/hardware-profiles.md)
