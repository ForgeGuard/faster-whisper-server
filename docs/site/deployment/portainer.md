---
title: Portainer
description: Deploy the x86 and Jetson stacks through Portainer on managed remote Docker hosts.
order: 42
status: stable
---

# Portainer

Portainer manages Docker on remote hosts through a web UI. The repository ships
two ready-to-use stack files — one for x86 NVIDIA hosts and one for Jetson — that
you can paste into a Portainer stack. They differ mainly in how the GPU is exposed
and which model and compute type are used, so read the one that matches your
hardware.

## Prerequisites

- A Portainer-managed Docker host with the NVIDIA Container Toolkit installed.
- Ability to pull `ghcr.io/forgeguard-ai/...` images on that host.

## x86 NVIDIA stack

`deploy/docker-compose.portainer.yml`:

- **Image**: `ghcr.io/forgeguard-ai/faster-whisper-server:latest`.
- **Port**: `8000:8000` (plain HTTP; no TLS block).
- **Environment**: `MODEL_SIZE: large-v3`, `DEVICE: cuda`,
  `COMPUTE_TYPE: float16`, `BEAM_SIZE: "5"`, `ENABLE_VAD_FILTER: "true"`,
  `DEFAULT_LANGUAGE: ""`, `API_KEY: ""` (open by default), `WARMUP_ON_START: "true"`.
- **GPU**: `deploy.resources.reservations.devices`
  (`driver: nvidia, count: 1, capabilities: [gpu]`).
- **Volume**: `faster-whisper-cache` at `/home/appuser/.cache/huggingface` (the
  `large-v3` model is baked in; the cache is only used for non-baked sizes).
- **Health check**: `curl -fsS http://127.0.0.1:8000/health`.

## Jetson stack

`deploy/docker-compose.portainer.jetson.yml`:

- **Image**: `ghcr.io/forgeguard-ai/faster-whisper-server-jetson:latest`.
- **GPU runtime**: `runtime: nvidia` with `NVIDIA_VISIBLE_DEVICES: all` and
  `NVIDIA_DRIVER_CAPABILITIES: all` — Jetson uses the NVIDIA runtime rather than
  `deploy.resources`.
- **Port**: `8000:8000`.
- **Jetson-specific environment**: `MODEL_SIZE: small`, `DEVICE: cuda`,
  `COMPUTE_TYPE: int8_float16` (float16 OOMs on the 8 GB Orin), plus the same
  `BEAM_SIZE`, `ENABLE_VAD_FILTER`, `DEFAULT_LANGUAGE`, `API_KEY`, and
  `WARMUP_ON_START` values as the x86 stack.
- **Volume**: `faster-whisper-cache` at `/home/appuser/.cache/huggingface`.

See [Hardware profiles](./hardware-profiles.md) and the
[Jetson troubleshooting](../troubleshooting/jetson.md) page for the memory
constraints behind these Jetson defaults.

## Deploy in Portainer

1. In Portainer, go to **Stacks → Add stack**.
2. Give the stack a name and paste the contents of the matching Compose file
   (**web editor**), or point Portainer at the repository.
3. Adjust environment variables — at minimum set `API_KEY` if the host is
   reachable by anyone you do not fully trust.
4. Deploy, then confirm readiness by requesting `/ready` on the host's published
   port.

## Security note

Both bundled stacks leave `API_KEY` empty (open) and serve plain HTTP for
simplicity. Before exposing a stack beyond a trusted network, set an `API_KEY` and
put TLS in front of it (built-in TLS or a reverse proxy / ingress) — see
[Security hardening](../operations/security-hardening.md).
