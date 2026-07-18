# Development environment

Maintainer setup for working on ForgeGuard Faster Whisper Server. This is
contributor-facing material kept out of the published website; the quick guide is
in [`CONTRIBUTING.md`](../../../CONTRIBUTING.md).

The project ships as **container images and a Helm chart only** — there is no
supported bare-metal run path, and the dev workflow reflects that: run tests with
`uv`, exercise the server in a container.

## Dev container (recommended)

The repo ships a multi-arch dev container (`.devcontainer/`, amd64 + arm64 — it
works on x86 workstations and on Jetson devices directly). Open the folder in VS
Code and "Reopen in Container": you get Python 3.10 + uv (deps synced
automatically), Node 22 for the web console, Helm, and docker-outside-of-docker so
`docker build` / `docker compose` drive the host daemon (including its GPU
runtime).

## Prerequisites (without the dev container)

- [Docker](https://docs.docker.com/engine/install/) with the
  [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
  to exercise GPU inference.
- [uv](https://docs.astral.sh/uv/) for Python environments (tests and linting).

No native audio libraries are required for the unit tests: faster-whisper decodes
via PyAV (which bundles FFmpeg's libraries) and its onnxruntime/ctranslate2 wheels
are self-contained.

```bash
git clone https://github.com/forgeguard-ai/faster-whisper-server.git
cd faster-whisper-server
```

## Running the server

The dev loop is the container. A plain build + run:

```bash
docker build -f docker/Dockerfile -t faster-whisper-server:dev .
docker run --rm --gpus all -p 8000:8000 faster-whisper-server:dev
```

For the Jetson image, build `docker/jetson/Dockerfile` on an arm64 machine (or the
device itself) and run with `--runtime nvidia`.

## Web console

The console lives in `webui/` (Vite + React). Inside `webui/`, `npm ci && npm run
dev` gives a hot-reloading UI against a running server. Production builds happen
inside the Docker build (the `node:22-slim` stage), and `webui/dist` is baked into
the image at `/app/webui_dist`.

## Building images

Both images bake model weights at build time (`DOWNLOAD_MODEL=true`, fetching from
Hugging Face pinned to a specific Systran revision) and build the web console in a
Node stage — no network is needed at container start.

```bash
# x86 CUDA (cu128)
docker build -f docker/Dockerfile -t faster-whisper-server:dev .

# Jetson (arm64, on-device or on an arm64 builder)
docker build -f docker/jetson/Dockerfile -t faster-whisper-server-jetson:dev .
```

Build arguments include `MODEL_SIZE`, `MODEL_REVISION`, `DOWNLOAD_MODEL`, and (x86
only) `EXTRA_MODELS`.

## Next

- [Testing](./testing.md) — the test suite and linting.
- [Release process](../release/release-process.md) — cutting a versioned release.
