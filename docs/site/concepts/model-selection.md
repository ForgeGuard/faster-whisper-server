---
title: Model selection
description: Choose, provision, activate, and persist a Whisper model profile.
order: 21
status: stable
---

# Model selection

The server loads a single resident Whisper model and can switch it at runtime.
This page covers which model runs, how it is provisioned, and how to change it.

## The configured default

`MODEL_SIZE` sets the model loaded at startup (default `large-v3` on the x86
image, `small` on the Jetson image, matching each image's baked default). It can
be a size alias or a CTranslate2 repository id. `DEVICE` and `COMPUTE_TYPE`
control where and how it runs — see
[Environment variables](../configuration/environment-variables.md).

## Baked models vs. Hugging Face downloads

Models are resolved from two sources:

- **Baked** — the published images bake their default model plus `tiny` into
  `MODEL_DIR` (`/app/models/<size>`). When `<MODEL_DIR>/<size>/model.bin` exists,
  that copy is used and no download happens. The x86 image bakes `large-v3` +
  `tiny`; the Jetson image bakes `small` + `tiny`.
- **Hugging Face** — any other size is downloaded from the hub on first use.
  Canonical Systran repositories are pinned to a vetted git revision; a custom
  repo id or an explicit `MODEL_REVISION` bypasses that pin and is fetched as
  specified.

> **Persist the download cache.** A model that is not baked in is fetched into the
> Hugging Face cache. Mount a volume at `/home/appuser/.cache/huggingface` to keep
> it across restarts. **Never** mount a volume over `/app/models` — that would
> shadow the baked weights. See
> [Model provisioning](../troubleshooting/model-provisioning.md).

## Switching the model at runtime

The web console model picker (and the admin API) switch the resident model
without restarting the container. Available presets:

| Size | Parameters |
|---|---|
| `tiny` | 39M |
| `base` | 74M |
| `small` | 244M |
| `medium` | 769M |
| `large-v3` | 1550M |
| `large-v3-turbo` | 809M |
| `distil-large-v3` | 756M |

A custom `MODEL_SIZE` that is not in this list is also selectable. Activation is
an authenticated operation:

```bash
curl -X POST http://localhost:8000/api/model/activate \
  -H 'Authorization: Bearer change-me' \
  -H 'Content-Type: application/json' \
  -d '{"size": "large-v3-turbo"}'
```

Switching **unloads the current model, frees GPU memory, and loads the new one**;
the server reports `warming` during the swap. A size that is not baked in is
downloaded on first activation. See the
[Model admin API reference](../reference/model-admin-api.md) for request and error
shapes.

## Persistence across restarts

The active choice is written to `<DATA_DIR>/active_model` and resumed on the next
start. Mount `DATA_DIR` (default `/data`) as a volume so the selection — and the
generated TLS certificate — survive restarts.

## Baking extra models at build time

To avoid first-use downloads for additional sizes on the x86 image, bake them in:

```bash
docker build -f docker/Dockerfile \
  --build-arg EXTRA_MODELS="large-v3-turbo" \
  -t faster-whisper-server:custom .
```

The Jetson image does not expose an `EXTRA_MODELS` build argument.

## Related

- [Model lifecycle](../architecture/model-lifecycle.md) — warmup, activation, and
  readiness transitions.
- [Hardware profiles](../deployment/hardware-profiles.md) — which sizes fit which
  hardware.
