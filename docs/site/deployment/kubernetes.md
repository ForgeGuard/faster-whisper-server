---
title: Kubernetes (Helm)
description: Deploy to a cluster with the bundled Helm chart, wiring probes, GPU limits, and secrets.
order: 43
status: stable
---

# Kubernetes (Helm)

The repository ships a Helm chart (`charts/faster-whisper-server`) published as an
OCI artifact. It wires the health contract into Kubernetes probes and applies a
hardened security context by default.

## Prerequisites

- A Kubernetes cluster with GPU nodes and the NVIDIA device plugin, so
  `nvidia.com/gpu` resources are schedulable.
- Helm 3 with OCI support.

## Install

```bash
helm install whisper \
  oci://ghcr.io/forgeguard-ai/charts/faster-whisper-server \
  --version 1.1.0
```

The chart version and `appVersion` are both `1.1.0`. The image defaults to
`ghcr.io/forgeguard-ai/faster-whisper-server` at the chart's `appVersion`; override
`fasterWhisper.tag` to pin a different image tag.

## Probes and the health contract

The chart maps the server's lifecycle onto Kubernetes probes so pods receive
traffic only after warmup, without being restarted during it:

| Probe | Path | Notes |
|---|---|---|
| `startupProbe` | `/ready` | `periodSeconds: 5`, `failureThreshold: 60` — allows up to ~300 s cold load |
| `readinessProbe` | `/ready` | `periodSeconds: 10` — gates Service endpoints |
| `livenessProbe` | `/health` | `periodSeconds: 30` — restarts only on a terminal failure |

The chart overrides the image entrypoint to run
`uvicorn server.main:app --host 0.0.0.0 --port 8000` directly.

## GPU scheduling

The deployment requests and limits `nvidia.com/gpu: 1` by default. Adjust through
the chart's `resources` values.

## API key as a Secret

Authentication is off unless you enable it. Provide the key from an existing
Secret:

```yaml
fasterWhisper:
  apiKey:
    enabled: true
    existingSecret: whisper-api-key   # required when enabled
    secretKey: api-key                # key within the Secret
```

When enabled, the deployment injects `API_KEY` from the Secret via
`secretKeyRef`. Create the Secret first — templating fails if `existingSecret` is
empty:

```bash
kubectl create secret generic whisper-api-key --from-literal=api-key='change-me'
```

## Security context

The chart sets a hardened context by default: pod `runAsNonRoot: true`,
`runAsUser: 1000`, `fsGroup: 1000`; container `runAsNonRoot`, `runAsUser: 1000`,
`allowPrivilegeEscalation: false`, and `capabilities.drop: [ALL]`. A
`readOnlyRootFilesystem` line is present but commented out — it is compatible only
when the writable paths (`/tmp`, the Hugging Face cache, and `DATA_DIR`) are
mounts. See [Security hardening](../operations/security-hardening.md).

## Ingress and autoscaling

Both are opt-in. `ingress.enabled` renders a `networking.k8s.io/v1` Ingress
(default class `nginx`, host `whisper.example.com`); terminate TLS at the ingress
for public traffic. `autoscaling.enabled` renders an `autoscaling/v2` HPA
(default `minReplicas: 1`, `maxReplicas: 100`, `targetCPUUtilizationPercentage:
80`); the deployment omits a fixed `replicas` when autoscaling is on.

> **Note.** The chart ships no PersistentVolumeClaim template and mounts no
> volumes — it relies on the baked model. If you switch to a non-baked model at
> runtime, plan for the download to happen in-pod and be lost on reschedule unless
> you add your own volume.

## Extra environment and model choice

Set any environment variable (for example `MODEL_SIZE`, `COMPUTE_TYPE`) through
`fasterWhisper.extraEnv` as name/value pairs. Run `helm test` (the chart's
`test-connection` hook) to confirm the Service answers `/health`.

## Related

- [Health and readiness](../operations/health-and-readiness.md) — the contract the
  probes rely on.
- [Upgrades](../operations/upgrades.md) — rolling to a new image or chart version.
