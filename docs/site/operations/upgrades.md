---
title: Upgrades
description: Release and tagging policy, and how to roll containers and the Helm release to a new version.
order: 53
status: stable
---

# Upgrades

Images and the Helm chart are versioned together with the code. This page covers
the tagging policy and how to upgrade each deployment method.

## Tagging policy

- Pin an **immutable release tag** (for example `:1.1.0`) for persistent
  deployments.
- `:latest` (and the `-cu128` / `-jetson` `latest` aliases) tracks the newest
  stable release and can change without notice — convenient for testing, not for
  reproducible production.
- The Helm chart version and `appVersion` move together with each release.

## What persists across a restart

Mounted `DATA_DIR` state survives restarts and upgrades:

- The generated TLS certificate under `<DATA_DIR>/tls` — reused rather than
  regenerated.
- The persisted active-model choice in `<DATA_DIR>/active_model` — the server
  resumes the last activated size.

Keep `DATA_DIR` on a durable volume so an upgrade does not regenerate the
certificate or reset the model selection.

## Upgrading a container

```bash
docker pull ghcr.io/forgeguard-ai/faster-whisper-server:1.1.0
docker rm -f whisper
docker run -d --name whisper --gpus all -p 8000:8000 \
  -v whisper-data:/data \
  ghcr.io/forgeguard-ai/faster-whisper-server:1.1.0
```

After the container restarts it warms the model again; wait for `/ready` to return
`200` before sending traffic.

## Upgrading Compose

```bash
# edit the image tag in your compose file, then:
docker compose -f deploy/docker-compose.local.yml pull
docker compose -f deploy/docker-compose.local.yml up -d
```

## Upgrading the Helm release

```bash
helm upgrade whisper \
  oci://ghcr.io/forgeguard-ai/charts/faster-whisper-server \
  --version 1.1.0
```

During a rolling update, the `startupProbe` and `readinessProbe` on `/ready` hold
new pods out of the Service until their model has warmed, so the rollout does not
send traffic to a pod that cannot yet transcribe. See
[Health and readiness](./health-and-readiness.md).

## Verifying an upgrade

1. `curl .../health` returns `healthy` with the expected `model` and `device`.
2. `curl .../ready` returns `200`.
3. A sample transcription returns the expected transcript.
4. `curl .../system` shows the expected version and model.

## Related

- [Kubernetes (Helm)](../deployment/kubernetes.md)
- [Health and readiness](./health-and-readiness.md)
