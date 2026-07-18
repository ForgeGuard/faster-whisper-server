---
title: Jetson
description: Memory constraints and model choices for NVIDIA Jetson Orin.
order: 82
status: stable
---

# Jetson

The Jetson Orin profile trades model size for the device's shared-memory budget.
Most Jetson issues are memory pressure.

## Shared memory budget

The 8 GB Orin shares RAM between CPU and GPU. There is no separate VRAM pool, so a
model that would fit comfortably on a discrete GPU can exhaust the Orin. This is
why the Jetson image defaults to the `small` model with
`COMPUTE_TYPE=int8_float16` rather than `large-v3` / `float16`.

## Run the Jetson image

```bash
docker run -d --name whisper --runtime nvidia -p 8000:8000 \
  ghcr.io/forgeguard-ai/faster-whisper-server-jetson:latest
```

Jetson uses the NVIDIA runtime (`--runtime nvidia`), not `--gpus all`. The
Portainer Jetson stack sets `NVIDIA_VISIBLE_DEVICES` and
`NVIDIA_DRIVER_CAPABILITIES` explicitly — see [Portainer](../deployment/portainer.md).

## Before increasing the model size

The defaults are chosen to fit. Before moving to `medium` or `large-v3`:

1. Watch memory with `tegrastats` or `jtop` while transcribing.
2. Confirm there is real headroom under peak load, not just at idle.
3. Change one thing at a time — size or compute type — and re-measure.

If the container is killed or the model fails to load with an out-of-memory
symptom, step back down to `small` / `int8_float16`.

## Compute type

`int8_float16` keeps weights small while retaining useful precision on the Orin.
`float16` alone tends to OOM. If you experiment, keep `int8_float16` as the known-
good fallback.

## Slow first request

Warmup and first-request latency are longer on the Orin than on a datacenter GPU.
Keep `WARMUP_ON_START=true` (the default) so the model warms in the background and
`/ready` reflects when it can transcribe. See
[Health and readiness](../operations/health-and-readiness.md).

## Related

- [Hardware profiles](../deployment/hardware-profiles.md)
- [Model provisioning](./model-provisioning.md)
