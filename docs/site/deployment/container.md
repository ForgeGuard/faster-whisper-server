---
title: Container deployment
description: Run the server as a single container with GPU access, volumes, and environment.
order: 40
status: stable
---

# Container deployment

The single-container path is the simplest way to run the server for local testing
or a single-service deployment.

## Prerequisites

- Docker with the NVIDIA Container Toolkit for GPU inference on an x86_64 NVIDIA
  GPU. A CPU-only run works with reduced throughput.
- For Jetson Orin, use the Jetson image and NVIDIA runtime — see
  [Hardware profiles](./hardware-profiles.md).

## Images

| Hardware | Image | Baked model |
|---|---|---|
| x86_64 NVIDIA (CUDA cu128) | `ghcr.io/forgeguard-ai/faster-whisper-server:latest` (alias `-cu128`) | `large-v3` + `tiny` |
| NVIDIA Jetson Orin (JetPack 6) | `ghcr.io/forgeguard-ai/faster-whisper-server-jetson:latest` | `small` + `tiny` |

Both images expose port `8000`, run as a non-root user (uid 1000), and declare a
`/data` volume. Pin a release tag (for example `:1.1.0`) for stable deployments;
`:latest` tracks the newest release.

## Run it

```bash
docker run -d --name whisper --gpus all -p 8000:8000 \
  -v whisper-data:/data \
  ghcr.io/forgeguard-ai/faster-whisper-server:latest
```

Verify with `curl http://localhost:8000/health` and
`curl http://localhost:8000/ready`. See
[Health and readiness](../operations/health-and-readiness.md).

## Volumes

| Mount | Purpose | Notes |
|---|---|---|
| `/data` (`DATA_DIR`) | TLS cert/key and the persisted active-model choice | Mount to keep TLS certs and model selection across restarts |
| `/home/appuser/.cache/huggingface` | Hugging Face download cache | Mount when using a model **not** baked into the image |

> **Do not mount a volume over `/app/models`.** That directory holds the baked
> weights; mounting over it shadows them and forces a download. See
> [Model provisioning](../troubleshooting/model-provisioning.md).

## Common environment

```bash
docker run -d --name whisper --gpus all -p 8000:8000 \
  -v whisper-data:/data \
  -e API_KEY=change-me \
  -e MODEL_SIZE=large-v3 \
  ghcr.io/forgeguard-ai/faster-whisper-server:latest
```

The full list is in [Environment variables](../configuration/environment-variables.md).
For authentication and TLS, see
[Security hardening](../operations/security-hardening.md).

## CPU-only

For a machine without a GPU (for example a quick functional test), drop `--gpus`
and set the device:

```bash
docker run -d --name whisper -p 8000:8000 \
  -e DEVICE=cpu -e MODEL_SIZE=tiny \
  ghcr.io/forgeguard-ai/faster-whisper-server:latest
```

`COMPUTE_TYPE` auto-selects `int8` on CPU. Expect substantially lower throughput.

## Next steps

- Durable single-host operation → [Compose](./compose.md)
- Managed remote Docker → [Portainer](./portainer.md)
- Cluster / production → [Kubernetes](./kubernetes.md)
