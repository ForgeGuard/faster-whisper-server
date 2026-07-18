---
title: Configuration overview
description: How the server is configured, and which routes require authentication.
order: 30
status: stable
---

# Configuration overview

All configuration is through environment variables — there is no config file to
mount. This page explains the configuration model and the authentication
boundary; the full list of variables is in
[Environment variables](./environment-variables.md).

## How settings are read

Configuration is read from the environment **once at process start**
(`server/config.py`). Changing a variable requires restarting the container. Set
variables with `-e` on `docker run`, an `environment:` block in Compose, or the
chart's `fasterWhisper.extraEnv` in Kubernetes.

Boolean variables accept `1`, `true`, `yes`, or `on` (case-insensitive) for true;
anything else is false.

## Ports and binding

The service listens on port `8000` inside the container. The
`python -m server` entrypoint binds `HOST` (`0.0.0.0`) and `PORT` (`8000`); the
Helm chart instead runs `uvicorn ... --host 0.0.0.0 --port 8000` directly. Publish
or map the port as your deployment requires — for example the local Compose stack
maps host `8443` to container `8000` because it serves HTTPS.

## Authentication boundary

Authentication is **off by default**. Leaving `API_KEY` unset (the default) makes
the API open. Setting it requires every protected route to send
`Authorization: Bearer <key>`.

| Route | Method | Requires `API_KEY` when set |
|---|---|---|
| `/health`, `/ready` | GET | No — always open (orchestrator probes) |
| `/system` | GET | No — always open (non-PII telemetry) |
| `/web`, `/web/*` | GET | No — the console loads before a key is entered |
| `/docs`, `/openapi.json` | GET | No |
| `/v1/audio/transcriptions`, `/v1/audio/translations` | POST | **Yes** |
| `/v1/models` | GET | **Yes** |
| `/api/model/presets`, `/api/model/activate` | GET / POST | **Yes** |

Key comparison is constant-time, and a malformed (non-ASCII) token returns a clean
`401` rather than a `500`. When auth is enabled, the web console stores the key in
its settings and sends the bearer header on API calls; `/health`, `/ready`, and
`/system` stay open so the console and orchestrators work before a key is present.

> Enabling `API_KEY` does not enable TLS, and vice versa. Use a placeholder like
> `change-me` in examples and set a strong key in production.

## Common configuration surfaces

- **Model and inference** — `MODEL_SIZE`, `DEVICE`, `COMPUTE_TYPE`, `BEAM_SIZE`,
  `DEFAULT_LANGUAGE`, `ENABLE_VAD_FILTER`. See
  [Model selection](../concepts/model-selection.md).
- **Lifecycle** — `WARMUP_ON_START`, `MAX_CONCURRENCY`, `QUEUE_SIZE`,
  `QUEUE_TIMEOUT_S`. See [Health and readiness](../operations/health-and-readiness.md)
  and [Observability and queues](../operations/observability-and-queues.md).
- **Security and privacy** — `API_KEY`, `MAX_UPLOAD_BYTES`, `LOG_INPUT_TEXT`, the
  `TLS_*` group. See [Security hardening](../operations/security-hardening.md).
- **Storage** — `DATA_DIR`, `MODEL_DIR`. See
  [Container deployment](../deployment/container.md).

## Related

- [Environment variables](./environment-variables.md) — the complete table.
- [Configuration reference](../reference/configuration.md) — canonical values and
  defaults for tooling.
