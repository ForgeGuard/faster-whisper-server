---
title: Configuration reference
description: Canonical environment-variable names, defaults, and types in a compact form.
order: 72
status: stable
---

# Configuration reference

A compact, canonical list of every environment variable. For grouped explanations
see [Configuration overview](../configuration/overview.md) and
[Environment variables](../configuration/environment-variables.md).

| Variable | Type | Default | Notes |
|---|---|---|---|
| `HOST` | string | `0.0.0.0` | Bind address (`python -m server` entrypoint) |
| `PORT` | int | `8000` | Bind port (`python -m server` entrypoint) |
| `DATA_DIR` | string | `/data` | Writable state (TLS cert/key, `active_model`) |
| `UVICORN_ROOT_PATH` | string | *(unset)* | Reverse-proxy path prefix |
| `MODEL_SIZE` | string | `large-v3` (x86) / `small` (Jetson) | Size alias or CTranslate2 repo id |
| `DEVICE` | string | `cuda` | `cuda` \| `cpu` \| `auto` |
| `COMPUTE_TYPE` | string | `float16` (cuda) / `int8` (cpu) / `default` | Explicit value wins |
| `BEAM_SIZE` | int | `5` | Beam-search width |
| `DEFAULT_LANGUAGE` | string | *(auto)* | Fallback source language |
| `ENABLE_VAD_FILTER` | bool | `true` | Voice-activity-detection filter |
| `MODEL_DIR` | string | `/app/models` | Baked-model dir; empty forces hub download |
| `MODEL_REVISION` | string | *(unset)* | HF git revision override |
| `WARMUP_ON_START` | bool | `true` | Eager background warmup vs lazy load |
| `MAX_CONCURRENCY` | int | `1` | Concurrent transcriptions |
| `QUEUE_SIZE` | int | `32` | Max waiting requests |
| `QUEUE_TIMEOUT_S` | float | `120` | Seconds to wait for a slot |
| `API_KEY` | string | *(unset)* | Bearer key; unset = open |
| `MAX_UPLOAD_BYTES` | int | `26214400` | Upload cap (25 MB); `0` disables |
| `LOG_INPUT_TEXT` | bool | `false` | Log transcript text (keep off) |
| `PERSIST_AUDIO` | bool | `false` | Reserved / not enforced |
| `RETENTION_DAYS` | int | `0` | Reserved / not enforced |
| `ENABLE_WEB_UI` | bool | `true` | Serve `/web` console |
| `WEBUI_DIST_DIR` | string | `/app/webui_dist` | Built console assets |
| `TLS_ENABLED` | bool | `false` | Serve HTTPS directly (`python -m server`) |
| `TLS_SELF_SIGNED` | bool | `true` | Auto-generate a self-signed cert |
| `TLS_CERT_FILE` | string | `<DATA_DIR>/tls/cert.pem` | Certificate path |
| `TLS_KEY_FILE` | string | `<DATA_DIR>/tls/key.pem` | Private key path |
| `TLS_CN` | string | `localhost` | Certificate common name |
| `TLS_SAN` | list | *(none)* | Extra SANs, comma-separated |

Booleans are true for `1`, `true`, `yes`, or `on` (case-insensitive).

> `PERSIST_AUDIO` and `RETENTION_DAYS` are declared but have no runtime effect;
> see [Privacy and responsible use](../concepts/privacy-and-responsible-use.md).
