# Testing

The unit suite runs on CPU/`int8` with the `tiny` model and does not require a
GPU. This is what CI runs.

## Run the suite

```bash
uv run --extra test pytest tests/
```

The suite downloads the ~75 MB `tiny` model on first run (a few transcription
tests do real inference of `docker/jfk.flac`); most other tests use fakes and do
not load a model. Test defaults are set in `tests/conftest.py`
(`DEVICE=cpu`, `MODEL_SIZE=tiny`, `COMPUTE_TYPE=int8`, `API_KEY=test-key`,
`ENABLE_WEB_UI=false`, `MODEL_DIR=""` to force the hub download path).

## Lint and format

```bash
uv run --extra test ruff check .
uv run --extra test ruff format .
```

CI runs `ruff check .` and the test suite (see `.github/workflows/ci.yml`; it is
currently `workflow_dispatch`-only).

## Run inside the image (no local uv)

```bash
docker build -f docker/Dockerfile -t faster-whisper-server:dev .
docker run --rm -u root -v "$PWD:/work" -w /work \
  -e PYTHONPATH=/work -e DEVICE=cpu -e COMPUTE_TYPE=int8 -e MODEL_SIZE=tiny \
  faster-whisper-server:dev \
  bash -c 'uv pip install --python /app/.venv/bin/python ".[test]" && \
           /app/.venv/bin/python -m pytest tests/'
```

## What the suite covers

- Health/readiness state machine and the exact `/health` and `/ready` bodies and
  status codes, including warming → ready → failed transitions and the
  `os._exit(1)` on terminal warmup failure.
- The inference warming guard (`model_warming` / `model_failed`), the OpenAI error
  envelope, and lazy-load readiness flip.
- The transcription/translation API: response formats (`text`, `json`,
  `verbose_json`, `srt`, `vtt`), word timestamps, language validation, and auth.
- Model-mode switching (`/api/model/activate`, `/api/model/presets`) and its
  persistence to `<DATA_DIR>/active_model`.
- Provisioning (baked vs hub, revision pinning) without network or model loads.
- `/system` telemetry shape and GPU degradation without a driver.
- TLS certificate generation (key mode `0600`, SANs, idempotency).

The admission-queue error paths (`queue_full`, `queue_timeout`) exist in the
server but are not yet exercised by the suite — add coverage when touching that
code.

## Configuration note

`server/config.py` reads the environment at import, so tests that vary config must
set variables before importing `server.*` (see the subprocess pattern in
`tests/test_provisioning.py`). The `reset_model_status` autouse fixture clears
module-level model state between tests.
