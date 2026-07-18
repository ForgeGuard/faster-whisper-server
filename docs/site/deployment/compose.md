---
title: Docker Compose
description: Run the server durably on a single host, optionally with built-in local TLS.
order: 41
status: stable
---

# Docker Compose

Docker Compose is the recommended way to run the server durably on a single GPU
host. The repository ships a local Compose stack you can adapt.

## The bundled local stack

The `deploy/docker-compose.local.yml` file in the repository builds the image
locally and brings the server up with built-in HTTPS on a single GPU. Its shape:

- **Builds** from `docker/Dockerfile` with build args `MODEL_SIZE: small` and
  `EXTRA_MODELS: large-v3-turbo` (the published images bake `large-v3` instead).
- **Publishes host `8443` → container `8000`**, because the stack serves HTTPS.
- **Environment**: `DEVICE: cuda`, `COMPUTE_TYPE: float16`, `TLS_ENABLED: "true"`,
  `TLS_SELF_SIGNED: "true"`, `TLS_CN: localhost`.
- **Volumes**: a `fw-data` volume at `/data` (TLS cert/key, active-model choice)
  and `fw-hf-cache` at `/home/appuser/.cache/huggingface` (download cache).
- **GPU**: reserved via `deploy.resources.reservations.devices`
  (`driver: nvidia, count: 1, capabilities: [gpu]`).
- **Health check**: an HTTPS `GET /health` with a 300 s start period to allow for
  a cold model load.

Bring it up and open the console over HTTPS:

```bash
docker compose -f deploy/docker-compose.local.yml up -d --build
# then browse to https://localhost:8443/web
```

Because the certificate is self-signed, your browser will warn that it is
untrusted — expected for local use. See
[Security hardening](../operations/security-hardening.md) for supplying a real
certificate or terminating TLS elsewhere.

## A minimal published-image stack

To run a published image (no local build) over plain HTTP:

```yaml
services:
  faster-whisper:
    image: ghcr.io/forgeguard-ai/faster-whisper-server:latest
    ports:
      - "8000:8000"
    environment:
      MODEL_SIZE: large-v3
      DEVICE: cuda
      COMPUTE_TYPE: float16
      # API_KEY: change-me        # uncomment to require bearer auth
    volumes:
      - fw-data:/data
      - fw-hf-cache:/home/appuser/.cache/huggingface
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped

volumes:
  fw-data:
  fw-hf-cache:
```

Prerequisites: Docker Compose v2 and the NVIDIA Container Toolkit. Verify with
`curl http://localhost:8000/ready` once the model has warmed.

## Related

- [Portainer](./portainer.md) — running the same stacks through a managed UI.
- [Hardware profiles](./hardware-profiles.md) — x86 vs. Jetson differences.
