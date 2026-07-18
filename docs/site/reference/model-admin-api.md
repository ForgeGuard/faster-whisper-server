---
title: Model admin API
description: List presets and switch the resident Whisper model at runtime.
order: 71
status: stable
---

# Model admin API

The model-admin routes list the available Whisper presets and switch the resident
model without restarting the container. Both require the bearer key when `API_KEY`
is set. They are **not** gated on model readiness, so you can switch models even
while the current one is warming or failed.

## `GET /api/model/presets`

Returns the active model, the currently loaded model, and the selectable presets.

```bash
curl -H 'Authorization: Bearer change-me' \
  http://localhost:8000/api/model/presets
```

Response shape:

```json
{
  "active": "large-v3",
  "loaded": "large-v3",
  "presets": [
    { "size": "tiny", "label": "Tiny", "params": "39M" },
    { "size": "large-v3-turbo", "label": "Large v3 Turbo", "params": "809M" }
  ]
}
```

### Presets

| Size | Label | Parameters |
|---|---|---|
| `tiny` | Tiny | 39M |
| `base` | Base | 74M |
| `small` | Small | 244M |
| `medium` | Medium | 769M |
| `large-v3` | Large v3 | 1550M |
| `large-v3-turbo` | Large v3 Turbo | 809M |
| `distil-large-v3` | Distil Large v3 | 756M |

A custom `MODEL_SIZE` that is not in this list is also selectable and is prepended
to the presets.

## `POST /api/model/activate`

Switches the resident model. Body: `{"size": "<preset or configured size>"}`.

```bash
curl -X POST http://localhost:8000/api/model/activate \
  -H 'Authorization: Bearer change-me' \
  -H 'Content-Type: application/json' \
  -d '{"size": "large-v3-turbo"}'
```

On success returns `200` with the updated presets info
(`{"active": "large-v3-turbo", "loaded": "large-v3-turbo", ...}`). The switch
unloads the current model, frees GPU memory, and loads the requested one — a size
that is not baked in is downloaded on first activation. The choice is persisted to
`<DATA_DIR>/active_model` and resumed on restart.

### Errors

| Status | Code | Cause |
|---|---|---|
| `400` | `invalid_model` | Size is not a known preset or the configured `MODEL_SIZE` |
| `401` | — | Missing/invalid bearer key |
| `503` | `model_load_failed` | The requested model failed to load |

## Related

- [Model selection](../concepts/model-selection.md) — provisioning and baking.
- [Model lifecycle](../architecture/model-lifecycle.md) — switch internals and
  persistence.
