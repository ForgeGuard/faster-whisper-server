---
title: Compatibility
description: Hardware and platform support, and how OpenAI API compatibility differs from exact parity.
order: 73
status: stable
---

# Compatibility

## Hardware and platforms

| Target | Status | Notes |
|---|---|---|
| NVIDIA CUDA (x86_64) | Supported | cu128 image; RTX 3000 Ampere → RTX 5000 Blackwell; bakes `large-v3` |
| NVIDIA Jetson Orin (arm64) | Supported | JetPack 6 image; bakes `small` with `int8_float16` |
| CPU | Supported | Auto-downgrades to `int8`; reduced throughput |
| AMD (ROCm) | Not currently supported | Planned; see project status |
| Intel | Not currently supported | Planned; see project status |
| Apple Silicon | Not supported | No published image |

Container engines: Docker with the NVIDIA Container Toolkit, and Kubernetes with
the NVIDIA device plugin. There is no supported bare-metal install path.

## API compatibility vs. OpenAI parity

The API is **OpenAI-compatible**, meaning existing OpenAI audio SDKs work by
pointing `base_url` at this server. It is **not** a byte-for-byte reimplementation
of the OpenAI service. Practical differences:

- **`model` is ignored.** The loaded Whisper model is used regardless of the
  `model` field; `/v1/models` reports `whisper-1` plus the loaded size.
- **`temperature` is accepted but ignored.**
- **Response formats.** `text`, `json`, `verbose_json`, `srt`, and `vtt` are
  supported. In `verbose_json`, word timings are a flattened top-level `words[]`
  array (matching OpenAI), not nested in segments.
- **Endpoints implemented.** `/v1/audio/transcriptions`,
  `/v1/audio/translations`, and `/v1/models`. Other OpenAI endpoints (chat,
  embeddings, and so on) are not part of this server.
- **Authentication.** Optional bearer `API_KEY` following the OpenAI
  `Authorization: Bearer` convention, but off by default.
- **Operational routes.** `/health`, `/ready`, `/system`, and `/api/model/*` are
  ForgeGuard additions, not part of the OpenAI API.

## Whisper models

Transcription quality, language coverage, and translation behavior come from the
underlying Whisper models. Available presets range from `tiny` to `large-v3` (see
[Model selection](../concepts/model-selection.md)). Language support follows
faster-whisper's supported language set; an unsupported `language` code returns
`400`.

## Versioning

The server, container images, and Helm chart share a version (currently `1.1.0`).
See [Upgrades](../operations/upgrades.md) for the tagging and release policy.
