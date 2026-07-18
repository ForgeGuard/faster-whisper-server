---
title: Hardware profiles
description: x86_64 CUDA and NVIDIA Jetson Orin profiles, their baked models, and compute types.
order: 44
status: stable
---

# Hardware profiles

Two hardware profiles are published, each with its own image, default model, and
compute type. Match your deployment to the right profile.

## x86_64 NVIDIA (CUDA cu128)

| Property | Value |
|---|---|
| Image | `ghcr.io/forgeguard-ai/faster-whisper-server:latest` (alias `-cu128`) |
| Base | `nvidia/cuda:12.8.1-cudnn-runtime-ubuntu22.04` |
| GPUs | RTX 3000 (Ampere) through RTX 5000 (Blackwell) |
| Baked model | `large-v3` + `tiny` |
| Default compute type | `float16` |
| GPU exposure | `--gpus all` / `deploy.resources.reservations.devices` |

This is the general-purpose datacenter/workstation profile. Warmup takes seconds
on a datacenter GPU. Bake additional sizes with the `EXTRA_MODELS` build argument
(see [Model selection](../concepts/model-selection.md)).

## NVIDIA Jetson Orin (JetPack 6)

| Property | Value |
|---|---|
| Image | `ghcr.io/forgeguard-ai/faster-whisper-server-jetson:latest` |
| Base | `nvcr.io/nvidia/l4t-jetpack:r36.4.0` (arm64) |
| Baked model | `small` + `tiny` |
| Default compute type | `int8_float16` |
| GPU exposure | `--runtime nvidia` (+ `NVIDIA_VISIBLE_DEVICES`, `NVIDIA_DRIVER_CAPABILITIES`) |

The Jetson image is built for the Orin's Compute Capability 8.7 with CTranslate2
compiled from source with CUDA support. Because the 8 GB Orin shares memory
between CPU and GPU, the profile defaults to the `small` model and
`int8_float16` — `float16` and larger models can exhaust memory. Confirm headroom
with `tegrastats` or `jtop` before increasing the model size or changing the
compute type. See [Jetson troubleshooting](../troubleshooting/jetson.md).

## Choosing a model per profile

- **x86 with ample VRAM** — `large-v3` (baked) for best quality, or
  `large-v3-turbo` for a faster large model.
- **Jetson Orin (8 GB)** — stay with `small` + `int8_float16`; test carefully
  before moving to `medium`.
- **CPU-only** — `tiny` or `base` with `int8` for functional testing; expect low
  throughput.

Warmup time and per-request latency scale with model size and hardware. See
[Model lifecycle](../architecture/model-lifecycle.md) for how loading and switching
behave.

## CPU fallback

Any image can run on CPU by setting `DEVICE=cpu`; `COMPUTE_TYPE` then
auto-selects `int8` (CTranslate2 cannot run `float16` on CPU). This is intended
for tests and small workloads, not production throughput.
