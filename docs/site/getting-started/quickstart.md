---
title: Quickstart
description: Run the container, verify health and readiness, and make your first transcription request.
order: 10
status: stable
---

# Quickstart

Get from zero to a working transcription in a few minutes.

## Prerequisites

- Docker with the
  [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
  for GPU inference on an x86_64 NVIDIA GPU (RTX 3000 Ampere → RTX 5000
  Blackwell). A CPU-only run works too, with reduced throughput.
- Outbound access to `ghcr.io` to pull the image. The default model is baked into
  the image, so no model download is needed at container start.
- An audio file to transcribe (`wav`, `mp3`, `m4a`, `flac`, `ogg`, `webm`, …).

## 1. Run the container

```bash
docker run -d --name whisper --gpus all -p 8000:8000 \
  ghcr.io/forgeguard-ai/faster-whisper-server:latest
```

This publishes the service on port `8000` and bakes the `large-v3` model. On
Jetson Orin, use the Jetson image and NVIDIA runtime instead:

```bash
docker run -d --name whisper --runtime nvidia -p 8000:8000 \
  ghcr.io/forgeguard-ai/faster-whisper-server-jetson:latest
```

The Jetson image bakes the `small` model — see
[Hardware profiles](../deployment/hardware-profiles.md).

## 2. Verify health and readiness

The server accepts connections immediately and warms the model in the background.
Two endpoints report distinct states:

```bash
curl http://localhost:8000/health   # 200 right away: {"status":"warming",...} then "healthy"
curl http://localhost:8000/ready    # 503 while warming, 200 once it can transcribe
```

Wait for `/ready` to return `200 {"status":"ready"}` before sending inference
requests. The full contract is documented in
[Health and readiness](../operations/health-and-readiness.md).

## 3. Make your first transcription request

```bash
curl -X POST http://localhost:8000/v1/audio/transcriptions \
  -F 'file=@audio.mp3' \
  -F 'response_format=text'
```

A plain-text transcript is returned. Try `response_format=json` for
`{"text": "..."}`, or `verbose_json` for segments and optional word timestamps —
see [Transcription and translation](../concepts/transcription-and-translation.md).

## 4. Use the OpenAI SDK

Any OpenAI audio client works by pointing `base_url` at the server:

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="not-needed")
with open("audio.mp3", "rb") as f:
    transcript = client.audio.transcriptions.create(model="whisper-1", file=f)
print(transcript.text)
```

The `model` field is accepted for compatibility but ignored; the loaded Whisper
model is used. When authentication is disabled, any `api_key` value is accepted.

## 5. Open the web console

Browse to `http://localhost:8000/web` to upload or record audio, pick a language
and response format, watch GPU telemetry, and switch models. Interactive API docs
are at `http://localhost:8000/docs`.

## Next steps

- Turn on authentication and TLS →
  [Configuration overview](../configuration/overview.md),
  [Security hardening](../operations/security-hardening.md)
- Run it durably → [Compose](../deployment/compose.md),
  [Kubernetes](../deployment/kubernetes.md)
- Tune the model → [Model selection](../concepts/model-selection.md)
- Something not working? → [Common errors](../troubleshooting/common-errors.md)
