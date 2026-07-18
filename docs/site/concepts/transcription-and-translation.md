---
title: Transcription and translation
description: How the transcription and translation endpoints, response formats, and decoding options behave.
order: 20
status: stable
---

# Transcription and translation

The server exposes two OpenAI-compatible speech endpoints. Both accept a
multipart form upload and return the transcript in the format you request.

## The two endpoints

| Endpoint | Task | Language behavior |
|---|---|---|
| `POST /v1/audio/transcriptions` | Transcribe speech in its original language | Auto-detects, or force with `language` |
| `POST /v1/audio/translations` | Translate speech **into English** | Always auto-detects the source; no `language` field |

Both endpoints require authentication only when an `API_KEY` is set (see
[Configuration overview](../configuration/overview.md)) and both return `503`
while the model is still warming (see
[Health and readiness](../operations/health-and-readiness.md)).

## Request fields

`transcriptions` accepts: `file` (required), `language` (optional; omit to
auto-detect), `prompt` (optional decoding hint), `response_format`,
`timestamp_granularities[]`, and `model` (accepted but ignored). `translations`
accepts `file`, `prompt`, and `response_format` — no `language` and no timestamp
granularities.

- **`language`** forces the source language (for example `es`). When omitted, the
  server falls back to `DEFAULT_LANGUAGE` if configured, otherwise Whisper
  auto-detects. An unsupported language code returns `400`.
- **`prompt`** biases decoding with an initial context string — useful for names,
  jargon, or acronyms. It maps to Whisper's `initial_prompt`.
- **Voice-activity detection** filtering is applied by default
  (`ENABLE_VAD_FILTER=true`) to skip non-speech.
- **Beam size** comes from `BEAM_SIZE` (default `5`).

## Response formats

`response_format` accepts five values. The default is `json`.

| Value | Body | Content type |
|---|---|---|
| `text` | Raw transcript | `text/plain` |
| `json` | `{"text": "..."}` | `application/json` |
| `verbose_json` | Task, language, duration, text, `segments[]`, optional `words[]` | `application/json` |
| `srt` | SubRip subtitle text (`HH:MM:SS,mmm`) | `text/plain` |
| `vtt` | WebVTT subtitle text (`HH:MM:SS.mmm`) | `text/plain` |

> The web console offers `text`, `json`, and `verbose_json`, and builds `.srt` /
> `.vtt` downloads on the client from `verbose_json` segments. The server also
> accepts `srt` and `vtt` as `response_format` values directly.

### Word-level timestamps

Add `timestamp_granularities[]=word` with `response_format=verbose_json` to get
per-word timings:

```bash
curl -X POST http://localhost:8000/v1/audio/transcriptions \
  -F 'file=@audio.mp3' \
  -F 'response_format=verbose_json' \
  -F 'timestamp_granularities[]=word'
```

Words are returned as a **flattened top-level `words` array** of
`{word, start, end, probability}` — they are not nested inside segments. Each
segment carries `id, seek, start, end, text, tokens, temperature, avg_logprob,
compression_ratio, no_speech_prob`. See the
[OpenAI-compatible API reference](../reference/openai-api.md) for the full schema.

## Translation

`POST /v1/audio/translations` takes the same multipart body minus `language` and
translates any supported source language into English:

```bash
curl -X POST http://localhost:8000/v1/audio/translations \
  -F 'file=@spanish.mp3' -F 'response_format=text'
```

## Related

- [Model selection](./model-selection.md) — which model produces these results.
- [Privacy and responsible use](./privacy-and-responsible-use.md) — how the audio
  and transcript are handled.
