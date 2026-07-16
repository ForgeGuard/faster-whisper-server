# syntax=docker/dockerfile:1

# --- Stage 1: build the web console (static assets only) ---
FROM node:22-slim AS webbuild
WORKDIR /web
COPY webui/package*.json ./
RUN npm ci
COPY webui/ ./
RUN npm run build          # emits /web/dist

# --- Stage 2: runtime (CUDA cu128 — RTX 3000 Ampere through RTX 5000 Blackwell) ---
FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu22.04

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends \
       python3 python3-venv curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# uv manages the virtualenv and installs the locked dependency set. Keeping the
# venv at /app/.venv (not a system install) is what lets CONTRIBUTING's
# "run tests inside the image" fallback work: `uv pip install --python /app/.venv/bin/python`.
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh
ENV UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:${PATH}"

# Dependency layer: pyproject + lock only, so source edits don't rebuild the venv.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-cache --python /usr/bin/python3

# Non-root user; the HF cache lives in its home for any runtime model overrides.
ENV HF_HOME=/home/appuser/.cache/huggingface
RUN useradd --create-home --uid 1000 appuser && mkdir -p "$HF_HOME"

# --- Model bake ---------------------------------------------------------------
# Baked models live at /app/models/<MODEL_SIZE>, OUTSIDE HF_HOME, so a cache
# volume mounted at HF_HOME (see deploy/) can never shadow them. Only the small
# provisioning import-chain is copied before the (large) bake layer, so ordinary
# edits to server code below do not invalidate the multi-GB download.
ENV MODEL_DIR=/app/models
COPY docker/scripts/download_model.py /app/docker/scripts/download_model.py
COPY server/__init__.py server/version.py server/provisioning.py /app/server/
COPY VERSION /app/VERSION
ARG MODEL_SIZE=large-v3
ARG MODEL_REVISION=
ARG DOWNLOAD_MODEL=true
# Extra models to also bake so they are selectable offline from the console's
# model picker (space-separated sizes, e.g. "large-v3-turbo"). Empty by default,
# so published images are unchanged; deploy/docker-compose.local.yml sets this.
ARG EXTRA_MODELS=""
# Promote the baked model to the runtime default so the image uses its baked
# weights (not config.py's default) when MODEL_SIZE is not overridden.
ENV MODEL_SIZE=${MODEL_SIZE}
RUN if [ "$DOWNLOAD_MODEL" = "true" ]; then \
      HF_HOME=/tmp/hf-build MODEL_REVISION="$MODEL_REVISION" \
        python3 /app/docker/scripts/download_model.py --model "$MODEL_SIZE" --output /app/models \
      && HF_HOME=/tmp/hf-build \
        python3 /app/docker/scripts/download_model.py --model tiny --output /app/models \
      && for m in $EXTRA_MODELS; do \
           HF_HOME=/tmp/hf-build \
             python3 /app/docker/scripts/download_model.py --model "$m" --output /app/models || exit 1; \
         done \
      && rm -rf /tmp/hf-build; \
    fi

# Application code + built web console.
COPY server/ /app/server/
COPY --from=webbuild /web/dist /app/webui_dist

# Persistent, writable state (TLS cert/key, active-model choice). The only path
# the non-root runtime needs to write; mount a named volume here in deploy/.
ENV DATA_DIR=/data
RUN mkdir -p /data

RUN chown -R appuser:appuser /app /home/appuser /data
USER appuser
VOLUME ["/data"]

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# Default healthcheck speaks HTTP. The TLS deploy (deploy/docker-compose.local.yml)
# overrides this to speak HTTPS with an unverified context.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:8000/health" || exit 1

# `python -m server` wraps uvicorn so TLS_ENABLED wires ssl_certfile/keyfile in;
# with TLS off it is behaviour-identical to the old `uvicorn server.main:app`.
CMD ["python3", "-m", "server"]
