# Jetson Orin Nano (aarch64) image.
#
# CTranslate2 (faster-whisper's inference backend) does not publish a CUDA-enabled
# aarch64 wheel on PyPI (PyPI aarch64 wheels are CPU-only), so it is compiled from
# source here with CUDA + cuDNN support targeting the Orin's Ampere GPU
# (Compute Capability 8.7).
#
# IMPORTANT: L4T_JETPACK_TAG must be compatible with the host's JetPack/L4T release.
# Check the host version with:
#   cat /etc/nv_tegra_release
# NVIDIA container images are compatible across minor revisions of the same major
# L4T line (e.g. an r36.4.0 container is expected to run on any R36.x host), but not
# across major lines (R35 vs R36). Adjust the default below if it stops matching.
ARG L4T_JETPACK_TAG=r36.4.0

# --- Web console build (arch-independent; node has arm64 images) ---
FROM node:22-slim AS webbuild
WORKDIR /web
COPY webui/package*.json ./
RUN npm ci
COPY webui/ ./
RUN npm run build          # emits /web/dist

FROM nvcr.io/nvidia/l4t-jetpack:${L4T_JETPACK_TAG} AS builder

# Kept in lockstep with the pinned ctranslate2 version in pyproject.toml/uv.lock
# so the source-built CUDA wheel and the locked dependency graph agree. Satisfies
# faster-whisper's `ctranslate2>=4.0,<5` requirement; validated on-device on Orin.
ARG CTRANSLATE2_VERSION=4.8.1
# Orin's GPU Compute Capability. Hardcoded because CI builds on a GitHub-hosted
# runner with no physical GPU present, so CTranslate2's CMake "Auto" architecture
# detection (which queries an attached GPU) cannot be used.
ARG CUDA_ARCH_LIST=8.7

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -y \
    && apt-get install -y --no-install-recommends \
       build-essential \
       cmake \
       git \
       python3-dev \
       python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt
RUN git clone --depth 1 --branch v${CTRANSLATE2_VERSION} --recursive \
    https://github.com/OpenNMT/CTranslate2.git

WORKDIR /opt/CTranslate2/build
RUN cmake .. \
       -DCMAKE_BUILD_TYPE=Release \
       -DWITH_CUDA=ON \
       -DWITH_CUDNN=ON \
       -DWITH_MKL=OFF \
       -DOPENMP_RUNTIME=COMP \
       -DCUDA_ARCH_LIST="${CUDA_ARCH_LIST}" \
       -DCMAKE_INSTALL_PREFIX=/opt/ctranslate2-install \
    && make -j"$(nproc)" \
    && make install

WORKDIR /opt/CTranslate2/python
RUN python3 -m pip install --no-cache-dir --upgrade pip \
    && python3 -m pip install --no-cache-dir -r install_requirements.txt \
    && LD_LIBRARY_PATH="/opt/ctranslate2-install/lib:${LD_LIBRARY_PATH}" \
       CTRANSLATE2_ROOT=/opt/ctranslate2-install \
       python3 setup.py --verbose bdist_wheel --dist-dir /opt/wheels

# ---

FROM nvcr.io/nvidia/l4t-jetpack:${L4T_JETPACK_TAG}

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends \
       python3 python3-venv curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Bring in the CUDA-enabled CTranslate2 build (shared libs + Python wheel).
COPY --from=builder /opt/ctranslate2-install/ /usr/local/
RUN ldconfig
COPY --from=builder /opt/wheels/*.whl /tmp/wheels/

# uv manages the venv (see amd64 Dockerfile for the CONTRIBUTING rationale).
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh
ENV UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:${PATH}"

# Dependency layer. `uv sync --frozen` installs the locked graph, including the
# CPU-only aarch64 ctranslate2 wheel from PyPI; the next step force-replaces it
# with the locally-built CUDA wheel (same version, so --no-deps keeps pins intact).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-cache --python /usr/bin/python3 \
    && uv pip install --python /app/.venv/bin/python --force-reinstall --no-deps /tmp/wheels/ctranslate2*.whl \
    && rm -rf /tmp/wheels

# Non-root user; HF cache in its home for runtime model overrides.
ENV HF_HOME=/home/appuser/.cache/huggingface
RUN useradd --create-home --uid 1000 appuser && mkdir -p "$HF_HOME"

# --- Model bake (small default for the 8 GB Orin) -----------------------------
# See the amd64 Dockerfile for the baked-outside-HF_HOME + import-chain-only
# caching rationale.
ENV MODEL_DIR=/app/models
COPY docker/scripts/download_model.py /app/docker/scripts/download_model.py
COPY server/__init__.py server/version.py server/provisioning.py /app/server/
COPY VERSION /app/VERSION
ARG MODEL_SIZE=small
ARG MODEL_REVISION=
ARG DOWNLOAD_MODEL=true
# Promote the baked model to the runtime default so the image uses its baked
# weights (not config.py's large-v3 default) when MODEL_SIZE is not overridden.
# int8_float16 is the memory-conscious default for the 8 GB Orin (float16 OOMs
# when coexisting with other GPU workloads); override COMPUTE_TYPE if you have
# headroom.
ENV MODEL_SIZE=${MODEL_SIZE} \
    COMPUTE_TYPE=int8_float16
RUN if [ "$DOWNLOAD_MODEL" = "true" ]; then \
      HF_HOME=/tmp/hf-build MODEL_REVISION="$MODEL_REVISION" \
        python3 /app/docker/scripts/download_model.py --model "$MODEL_SIZE" --output /app/models \
      && HF_HOME=/tmp/hf-build \
        python3 /app/docker/scripts/download_model.py --model tiny --output /app/models \
      && rm -rf /tmp/hf-build; \
    fi

# Application code + built web console.
COPY server/ /app/server/
COPY --from=webbuild /web/dist /app/webui_dist

# Persistent, writable state (TLS cert/key, active-model choice).
ENV DATA_DIR=/data
RUN mkdir -p /data

RUN chown -R appuser:appuser /app /home/appuser /data
USER appuser
VOLUME ["/data"]

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# Default healthcheck speaks HTTP; the TLS deploy overrides it for HTTPS.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:8000/health" || exit 1

# `python -m server` wraps uvicorn so TLS_ENABLED wires ssl in; behaviour-
# identical to `uvicorn server.main:app` when TLS is off.
CMD ["python3", "-m", "server"]
