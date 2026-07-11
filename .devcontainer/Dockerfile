# Dev environment for faster-whisper-server. Multi-arch: linux/amd64 and
# linux/arm64 (works on x86 workstations and on Jetson devices themselves).
#
# The server always RUNS as a container (see CONTRIBUTING.md) — this image is
# for editing, unit tests (CPU/int8), the web console, chart work, and driving
# docker builds via the host socket (docker-outside-of-docker).
FROM mcr.microsoft.com/devcontainers/python:1-3.10-bookworm

# faster-whisper's Python stack needs no native audio libraries (PyAV bundles
# FFmpeg's libraries, and the onnxruntime/ctranslate2 wheels are self-contained).
# ffmpeg (CLI) and jq are kept only as conveniences for poking at audio/the API.
# The base image ships a yarn apt source whose signing key has lapsed — drop it,
# we don't use yarn.
RUN rm -f /etc/apt/sources.list.d/yarn.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg jq \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# uv — Python env/deps runner used by tests and CI
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh

# Node 22 — web console (Vite/React) dev + build
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# helm — chart lint/template/package
RUN curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
