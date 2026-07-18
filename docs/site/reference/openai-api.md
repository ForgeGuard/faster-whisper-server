---
title: OpenAI-compatible API
description: Endpoints, request parameters, and response schemas for transcription and translation.
order: 70
status: stable
---

# OpenAI-compatible API

Everything under `/v1` follows the OpenAI audio API shape. Interactive docs are at
`/docs`. These routes require the bearer key when `API_KEY` is set.

## `POST /v1/audio/transcriptions`

Transcribe speech in its source language.

### Form fields

| Field | Required | Default | Notes |
|---|---|---|---|
| `file` | yes | — | Audio upload (multipart) |
| `model` | no | `whisper-1` | Accepted for compatibility, then ignored |
| `language` | no | auto / `DEFAULT_LANGUAGE` | Force a source language (e.g. `es`); unsupported codes return `400` |
| `prompt` | no | — | Initial decoding context (names, jargon) |
| `response_format` | no | `json` | `text`, `json`, `verbose_json`, `srt`, `vtt` |
| `timestamp_granularities[]` | no | — | Set to `word` with `verbose_json` for word timings |
| `temperature` | no | `0.0` | Accepted for compatibility, then ignored |

### Examples

```bash
# Plain text (text/plain), OpenAI-compatible
curl -X POST http://localhost:8000/v1/audio/transcriptions \
  -F 'file=@audio.mp3' -F 'response_format=text'

# {"text": "..."}
curl -X POST http://localhost:8000/v1/audio/transcriptions \
  -F 'file=@audio.mp3' -F 'response_format=json'
```

## `POST /v1/audio/translations`

Translate speech into English. Same multipart body as transcription **minus**
`language` and `timestamp_granularities` — the source language is always
auto-detected.

```bash
curl -X POST http://localhost:8000/v1/audio/translations \
  -F 'file=@spanish.mp3' -F 'response_format=text'
```

## Response formats

| Value | Body | Content type |
|---|---|---|
| `text` | Raw transcript | `text/plain` |
| `json` | `{"text": "..."}` | `application/json` |
| `verbose_json` | Object (see below) | `application/json` |
| `srt` | SubRip subtitles (`HH:MM:SS,mmm`) | `text/plain` |
| `vtt` | WebVTT subtitles (`WEBVTT` + `HH:MM:SS.mmm`) | `text/plain` |

### `verbose_json` schema

```json
{
  "task": "transcribe",
  "language": "en",
  "duration": 11.0,
  "text": "...",
  "segments": [
    {
      "id": 0, "seek": 0, "start": 0.0, "end": 3.2, "text": "...",
      "tokens": [50364, 400],
      "temperature": 0.0, "avg_logprob": -0.21,
      "compression_ratio": 1.4, "no_speech_prob": 0.02
    }
  ],
  "words": [
    { "word": "Ask", "start": 0.0, "end": 0.3, "probability": 0.98 }
  ]
}
```

- `segments[]` is always present in `verbose_json`.
- `words[]` is a **flattened top-level array** present only when
  `timestamp_granularities[]=word` was requested. Words are **not** nested inside
  segments (this matches the OpenAI shape).
- For `translations`, `task` is `translate` and there is no `words[]`.

### Word timestamps

```bash
curl -X POST http://localhost:8000/v1/audio/transcriptions \
  -F 'file=@audio.mp3' \
  -F 'response_format=verbose_json' \
  -F 'timestamp_granularities[]=word'
```

## `GET /v1/models`

Lists the configured model. Returns an OpenAI-style list whose ids include
`whisper-1` plus the loaded size (for example `tiny` or `large-v3`). Requires the
bearer key when `API_KEY` is set; it answers `200` even while the model is
warming.

## Errors

Errors use an OpenAI-shaped envelope:

```json
{ "error": { "message": "...", "type": "invalid_request_error", "code": 400 } }
```

A `detail` field is included alongside for the web console. Common cases:

| Status | Code / detail | Cause |
|---|---|---|
| `400` | `Unsupported response_format` | Unknown `response_format` |
| `400` | `Unsupported language: <code>` | Unknown `language` |
| `401` | `Invalid API key` | Missing/invalid bearer key |
| `413` | `Uploaded file is too large` | Body exceeds `MAX_UPLOAD_BYTES` |
| `503` | `model_warming` / `model_failed` | Model not ready (see [Health and readiness](../operations/health-and-readiness.md)) |
| `503` | `queue_full` / `queue_timeout` | Admission gate shed load |

See [Common errors](../troubleshooting/common-errors.md) for handling guidance and
[Compatibility](./compatibility.md) for parity notes.
