# Contributing to ForgeGuard Faster Whisper Server

Contributions are welcome. This project ships as **container images and a Helm
chart only** — there is no supported bare-metal run path, and the development
workflow reflects that: run tests with `uv`, exercise the server in a container.

## Dev container (recommended)

The repo ships a multi-arch dev container (`.devcontainer/`, amd64 + arm64 —
it works on x86 workstations and on Jetson devices directly). Open the folder
in VS Code and "Reopen in Container": you get Python 3.10 + uv (deps synced
automatically), Node 22 for the web console, helm, and docker-outside-of-docker
so `docker build`/`docker compose` drive the host daemon (including its GPU
runtime).

## Prerequisites

- [Docker](https://docs.docker.com/engine/install/) (with the
  [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
  if you want to exercise GPU inference)
- [uv](https://docs.astral.sh/uv/) for Python environments (tests and linting)

No native audio libraries are required to run the unit tests: faster-whisper
decodes via PyAV (which bundles FFmpeg's libraries) and its
onnxruntime/ctranslate2 wheels are self-contained. The suite downloads the
~75 MB `tiny` model on first run.

```bash
git clone https://github.com/forgeguard-ai/faster-whisper-server.git
cd faster-whisper-server
```

## Running tests

Unit tests run on CPU/int8 with the `tiny` model (this is what CI does):

```bash
uv run --extra test pytest tests/
```

Lint (imports are checked; `ruff` handles formatting too):

```bash
uv run --extra test ruff check .
uv run --extra test ruff format .
```

No local uv setup? Run the suite inside the server image instead:

```bash
docker build -f docker/Dockerfile -t faster-whisper-server:dev .
docker run --rm -u root -v "$PWD:/work" -w /work \
  -e PYTHONPATH=/work -e DEVICE=cpu -e COMPUTE_TYPE=int8 -e MODEL_SIZE=tiny \
  faster-whisper-server:dev \
  bash -c 'uv pip install --python /app/.venv/bin/python ".[test]" && \
           /app/.venv/bin/python -m pytest tests/'
```

## Running the server

The dev loop is the container. A plain build + run:

```bash
docker build -f docker/Dockerfile -t faster-whisper-server:dev .
docker run --rm --gpus all -p 8000:8000 faster-whisper-server:dev
```

For the Jetson image, build `docker/jetson/Dockerfile` on an arm64 machine (or
the device itself) and run with `--runtime nvidia`.

The web console lives in `webui/` (Vite + React). `npm ci && npm run dev` inside
`webui/` gives a hot-reloading UI against a running server; production builds are
done inside the Docker build (`webui/dist` is baked into the image).

## Submitting changes

1. Create a branch for your feature or fix.
2. Make your changes; keep them modular and in line with the current design.
   If you can't test on CUDA hardware, say so in the PR so a maintainer can.
3. Ensure `pytest` and `ruff check` pass and the affected image still builds.
4. Open a Pull Request against `main`.

Thank you for contributing!
