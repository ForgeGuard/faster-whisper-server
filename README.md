# ForgeGuard Faster Whisper Server

[![License](https://img.shields.io/badge/license-MIT-blue)](./LICENSE)
[![Changelog](https://img.shields.io/badge/changelog-white)](./CHANGELOG.md)
[![Model](https://img.shields.io/badge/model-whisper--large--v3-8A2BE2)](https://huggingface.co/Systran/faster-whisper-large-v3)

**ForgeGuard Faster Whisper Server** is a container-native, OpenAI-compatible
speech-to-text server built on
[faster-whisper](https://github.com/SYSTRAN/faster-whisper) and
[CTranslate2](https://github.com/OpenNMT/CTranslate2). An independent
ForgeGuard AI server originally derived from
[SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper)
(see [Attribution](#license--attribution)).

- **OpenAI-compatible** `/v1/audio/transcriptions` and `/v1/audio/translations`
  endpoints — point any OpenAI SDK at it
- **Multilingual** transcription with Whisper `large-v3`; `json`, `text`, and
  `verbose_json` responses with optional word-level timestamps
- **Voice-activity detection** filtering to skip silence
- **Instant health checks**: the server accepts connections immediately and warms
  the model in the background — orchestrator-friendly by design
- **Optional bearer auth** via a single `API_KEY` environment variable
- **Models baked into the images** — no downloads at container start
- Built-in **web console** at `/web` for uploading, recording, and transcribing

Distribution is **container images + a Helm chart only**. There is no supported
bare-metal install path.

| Hardware | Image |
|---|---|
| NVIDIA RTX 3000 → 5000 series (x86_64, CUDA cu128) | `ghcr.io/forgeguard-ai/faster-whisper-server:latest` (alias: `faster-whisper-server-cu128`, bakes `large-v3`) |
| NVIDIA Jetson Orin (arm64, JetPack 6) | `ghcr.io/forgeguard-ai/faster-whisper-server-jetson:latest` (bakes `small`) |
| AMD (ROCm), Intel | planned — see [Roadmap](#roadmap) |

`:latest` works, but pin a release tag (e.g. `:1.1.0`) for stable deployments.

<div align="center">
  <img src="assets/forgeguard-faster-whisper-server-web-ui.png" width="100%" alt="ForgeGuard Faster Whisper Server web console">
</div>

## Quick start

```bash
# NVIDIA amd64 (RTX 3000 through RTX 5000)
docker run -d --name whisper --gpus all -p 8000:8000 \
  ghcr.io/forgeguard-ai/faster-whisper-server:latest

# NVIDIA Jetson (arm64, Orin)
docker run -d --name whisper --runtime nvidia -p 8000:8000 \
  ghcr.io/forgeguard-ai/faster-whisper-server-jetson:latest
```

Then:

```bash
curl http://localhost:8000/health          # 200 immediately: "warming" -> "healthy"
curl http://localhost:8000/ready           # 200 once the model can transcribe

curl -X POST http://localhost:8000/v1/audio/transcriptions \
  -F 'file=@audio.mp3' \
  -F 'response_format=text'
```

- Interactive API docs: `http://localhost:8000/docs`
- Web console: `http://localhost:8000/web`

Or with the OpenAI SDK:

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="not-needed")

with open("audio.mp3", "rb") as f:
    transcript = client.audio.transcriptions.create(model="whisper-1", file=f)
print(transcript.text)
```

### Authentication

Unset `API_KEY` (the default) leaves the API open. Set it, and every API route
requires `Authorization: Bearer <key>`:

```bash
docker run -d --gpus all -p 8000:8000 -e API_KEY=change-me \
  ghcr.io/forgeguard-ai/faster-whisper-server:latest

curl -H 'Authorization: Bearer change-me' http://localhost:8000/v1/models
```

`/health`, `/ready`, and the web console stay open (the console stores a key in
its settings and sends the bearer header for API calls).

## Health & readiness contract

The server binds `0.0.0.0:8000` and accepts connections immediately; the model
loads and warms in a background task (~seconds on datacenter GPUs, longer on
edge devices). This keeps orchestrator health polls happy during warmup.

| Endpoint | While warming | Ready | Failed warmup |
|---|---|---|---|
| `GET /health` (liveness) | `200 {"status":"warming","model_loaded":false}` | `200 {"status":"healthy","model_loaded":true}` | `503` (then the process exits non-zero) |
| `GET /ready` (readiness) | `503` + `Retry-After` | `200 {"status":"ready"}` | `503` |
| `POST /v1/audio/transcriptions` | `503` + `Retry-After: 10`, error `model_warming` | normal | `503`, error `model_failed` |
| `GET /v1/models` | `200` (open during warmup) | `200` | `200` |

A warmup that fails permanently (e.g. missing weights) exits the container with
a non-zero code so restart policies and orchestrators see the failure instead
of a healthy-looking server that can't transcribe.

Set `WARMUP_ON_START=false` to skip eager loading; the model then loads lazily
on the first request.

## Configuration

All settings are environment variables (see [`server/config.py`](server/config.py)
for the full list):

| Variable | Default | Purpose |
|---|---|---|
| `MODEL_SIZE` | `large-v3` | Whisper model to load (size alias or a CTranslate2 repo id) |
| `DEVICE` | `cuda` | `cuda` or `cpu` |
| `COMPUTE_TYPE` | `float16` | CTranslate2 compute type (auto-downgraded to `int8` on CPU) |
| `BEAM_SIZE` | `5` | Beam search width |
| `DEFAULT_LANGUAGE` | *(auto)* | Force a source language instead of auto-detecting |
| `ENABLE_VAD_FILTER` | `true` | Skip non-speech with voice-activity detection |
| `API_KEY` | *(unset)* | When set, require `Authorization: Bearer <key>` on API routes |
| `WARMUP_ON_START` | `true` | Eagerly load + warm the model at startup (background task) |
| `MAX_UPLOAD_BYTES` | `26214400` | Reject uploads larger than this (25 MB; `0` disables) |
| `ENABLE_WEB_UI` | `true` | Serve the web console at `/web` |
| `MODEL_DIR` | `/app/models` | Directory of baked models (`<MODEL_DIR>/<MODEL_SIZE>`) |
| `MODEL_REVISION` | pinned for canonical Systran repos | Hugging Face git revision for hub downloads |
| `DATA_DIR` | `/data` | Writable state dir: TLS cert/key + persisted active-model choice |
| `MAX_CONCURRENCY` | `1` | Active transcriptions at once (feeds the `/system` activity meter) |
| `QUEUE_SIZE` | `32` | Max requests waiting for a slot before shedding with 503 |
| `LOG_INPUT_TEXT` | `false` | Log transcript text — **keep off**; transcripts are PII |
| `PERSIST_AUDIO` | `false` | Never keep uploaded audio beyond the request |
| `TLS_ENABLED` | `false` | Serve HTTPS directly (uvicorn SSL) — see below |
| `TLS_SELF_SIGNED` | `true` | Auto-generate a self-signed cert on first run if none supplied |
| `TLS_CERT_FILE` / `TLS_KEY_FILE` | `<DATA_DIR>/tls/...` | Provide your own cert/key instead |
| `TLS_CN` / `TLS_SAN` | `localhost` / *(none)* | CN and extra SANs for the generated cert |

See [`.env.example`](.env.example) for the complete, annotated list.

### Built-in HTTPS

Set `TLS_ENABLED=true` and the server speaks HTTPS directly — no reverse proxy,
no manual `openssl`. When no cert is supplied it generates a self-signed one on
first run (RSA 2048, SANs for the CN plus `localhost`/`127.0.0.1`/`::1`, ~10y
validity), persists it under `<DATA_DIR>/tls` with the key at mode `0600`, and
reuses it on every restart. Browsers warn on the self-signed cert (expected);
point `TLS_CERT_FILE`/`TLS_KEY_FILE` at a real cert for anything public.

The [`deploy/docker-compose.local.yml`](deploy/docker-compose.local.yml) stack
brings this up on a single local GPU with HTTPS on `https://localhost:8443/web`.

### Live GPU telemetry & the model picker

`GET /system` returns live GPU utilization/VRAM/temperature/power (best-effort
via NVML) plus in-flight/queued request counts. The web console renders a compact
monitor from it and a model-size picker: switch the resident Whisper model
(`tiny` … `large-v3`, `large-v3-turbo`, `distil-*`) at runtime with
`POST /api/model/activate` (auth-guarded); the choice persists to
`<DATA_DIR>/active_model` and resumes on restart. Sizes not baked into the image
download on first activation; bake extras at build time with
`--build-arg EXTRA_MODELS="large-v3-turbo"`.

See [docs/security.md](docs/security.md) and
[docs/responsible-use.md](docs/responsible-use.md) for data-handling and privacy
guidance (transcripts are sensitive PII).

## API overview

Everything under `/v1` is OpenAI-style. Full interactive reference at `/docs`.

<details>
<summary>Response formats</summary>

`response_format` accepts `json` (default), `text`, and `verbose_json`:

```bash
# Plain text body (text/plain), OpenAI-compatible
curl -X POST http://localhost:8000/v1/audio/transcriptions \
  -F 'file=@audio.mp3' -F 'response_format=text'

# {"text": "..."}
curl -X POST http://localhost:8000/v1/audio/transcriptions \
  -F 'file=@audio.mp3' -F 'response_format=json'
```
</details>

<details>
<summary>Word timestamps (verbose_json)</summary>

`verbose_json` returns per-segment detail; add `timestamp_granularities[]=word`
for word-level timings:

```bash
curl -X POST http://localhost:8000/v1/audio/transcriptions \
  -F 'file=@audio.mp3' \
  -F 'response_format=verbose_json' \
  -F 'timestamp_granularities[]=word'
```

The response includes `segments` (with `avg_logprob`, `no_speech_prob`,
`compression_ratio`, …) and a top-level `words` array of
`{word, start, end, probability}`.
</details>

<details>
<summary>Translation to English</summary>

`POST /v1/audio/translations` takes the same multipart body (minus `language`)
and translates any supported source language into English:

```bash
curl -X POST http://localhost:8000/v1/audio/translations \
  -F 'file=@spanish.mp3' -F 'response_format=text'
```
</details>

<details>
<summary>Language & prompt</summary>

- `language` forces the source language (e.g. `es`); omit it to auto-detect.
- `prompt` biases decoding with an initial context string (names, jargon).
- `GET /v1/models` lists the configured model (`whisper-1` plus the loaded size).
</details>

## Web console

A React console (pictured above) is served at `/web` for uploading or recording
audio and transcribing it: file upload and mic capture, language and
response-format selection, a model-warming banner, transcript copy and download
(`.txt`/`.srt`/`.vtt`), and API-key entry when auth is enabled. Disable it with
`ENABLE_WEB_UI=false`.

## Kubernetes (Helm)

```bash
helm install whisper oci://ghcr.io/forgeguard-ai/charts/faster-whisper-server --version 1.1.0
```

The chart (also in [`charts/faster-whisper-server`](charts/faster-whisper-server))
wires the health contract into probes: `startupProbe` and `readinessProbe` on
`/ready`, `livenessProbe` on `/health`, so pods receive traffic only after warmup
without being restarted during it. GPU scheduling uses `nvidia.com/gpu` limits
(default 1). API keys come from a Kubernetes Secret via
`fasterWhisper.apiKey.existingSecret`. See
[`values.yaml`](charts/faster-whisper-server/values.yaml) for ingress,
autoscaling, and probe tuning.

## Building

```bash
# amd64 CUDA (cu128)
docker build -f docker/Dockerfile -t faster-whisper-server:dev .

# Jetson (arm64, on-device or on an arm64 builder)
docker build -f docker/jetson/Dockerfile -t faster-whisper-server-jetson:dev .
```

Both images bake the model weights at build time (`DOWNLOAD_MODEL=true` build
arg, fetching from Hugging Face pinned to a specific Systran revision) and build
the web console in a Node stage — no network needed at container start. Release
images are published by
[`.github/workflows/release.yml`](.github/workflows/release.yml) on version tags.

## Testing

```bash
uv run --extra test pytest tests/
```

The unit suite runs on CPU/int8 with the `tiny` model and downloads it (~75 MB)
on first run. See [CONTRIBUTING.md](CONTRIBUTING.md) for the run-inside-the-image
fallback.

## Troubleshooting

<details>
<summary>CPU inference and float16</summary>

CTranslate2 cannot run `float16` on CPU. The server auto-downgrades to `int8`
when `DEVICE=cpu`, so a GPU-oriented config still starts on a CPU-only host.
</details>

<details>
<summary>Jetson Orin memory</summary>

The 8 GB Orin shares RAM between CPU and GPU. The Jetson image defaults to the
`small` model with `COMPUTE_TYPE=int8_float16`; bump to `medium`/`large-v3` only
after confirming headroom with `tegrastats`/`jtop`.
</details>

<details>
<summary>Using a model that isn't baked in</summary>

Overriding `MODEL_SIZE` to a model not baked into the image triggers a Hugging
Face download at first use. Mount a cache volume at
`/home/appuser/.cache/huggingface` to persist it across restarts. Never mount a
volume over `/app/models` — that would shadow the baked weights.
</details>

## Roadmap

- **Real-time streaming transcription** — first-class low-latency streaming for
  live and conversational/agent workloads: incremental partial transcripts over a
  persistent connection (WebSocket/SSE), time-to-first-token tuned chunking, and
  barge-in-friendly cancellation, alongside the existing OpenAI-style
  request/response endpoints.
- **More inference backends** — AMD (ROCm) and Intel images, plus newer
  inference libraries/frameworks as hardware becomes available to develop and
  validate on.

## License & attribution

This repository is licensed under the [MIT License](LICENSE); see
[NOTICE](NOTICE) for required attributions.

- Originally derived from [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper)
  (MIT) — the inference library this server builds on.
- [OpenAI Whisper](https://github.com/openai/whisper) model weights (MIT), as
  converted to CTranslate2 format by [Systran](https://huggingface.co/Systran).
- [CTranslate2](https://github.com/OpenNMT/CTranslate2) (MIT) — the inference
  engine.
