---
title: Model provisioning
description: Baked models, Hugging Face downloads, the cache volume, and the /app/models pitfall.
order: 81
status: stable
---

# Model provisioning

Most model problems come from where the weights are (or are not). This page covers
baked models, downloads, and the mount that most often breaks things.

## Baked vs. downloaded

- The published images bake their default model plus `tiny` into `MODEL_DIR`
  (`/app/models/<size>`). When `<MODEL_DIR>/<size>/model.bin` exists, that copy is
  used and nothing is downloaded.
- Any other size — for example switching to `medium` at runtime, or setting a
  `MODEL_SIZE` that is not baked — is downloaded from Hugging Face on first use.

## Never mount over `/app/models`

`MODEL_DIR` is deliberately outside the Hugging Face cache so a cache volume cannot
shadow it. **Mounting any volume over `/app/models` hides the baked weights**,
forcing a download (and failing if the container has no network). If you see an
unexpected download or a `model_failed` on an image that should have the model
baked in, check for a stray `/app/models` mount.

## Persisting downloads

A non-baked model is fetched into the Hugging Face cache at
`/home/appuser/.cache/huggingface`. Mount a volume there to keep it across
restarts and avoid re-downloading:

```bash
docker run -d --gpus all -p 8000:8000 \
  -e MODEL_SIZE=medium \
  -v whisper-hf-cache:/home/appuser/.cache/huggingface \
  ghcr.io/forgeguard-ai/faster-whisper-server:latest
```

## CPU inference and `float16`

CTranslate2 cannot run `float16` on CPU. When `DEVICE=cpu`, `COMPUTE_TYPE`
auto-selects `int8`, so a GPU-oriented configuration still starts on a CPU-only
host. Set `COMPUTE_TYPE` explicitly only if you need a specific type.

## Pinned revisions

Canonical Systran repositories (for example `large-v3`, `small`, `tiny`) download
at a vetted, pinned git revision. Providing a custom repository id or an explicit
`MODEL_REVISION` bypasses the pin and fetches exactly what you specify — useful for
community models, but you own the revision choice.

## Baking extra models

To avoid first-use downloads on the x86 image, bake additional sizes at build
time:

```bash
docker build -f docker/Dockerfile \
  --build-arg EXTRA_MODELS="large-v3-turbo distil-large-v3" \
  -t faster-whisper-server:custom .
```

`EXTRA_MODELS` is space-separated. The Jetson image does not expose this argument.

## Related

- [Model selection](../concepts/model-selection.md)
- [Common errors](./common-errors.md)
