# Release process

Releases publish the container images and the Helm chart, all versioned together.
This is maintainer-facing material kept out of the published website.

## Versioning

The `VERSION` file at the repository root is the single source of truth (currently
`1.1.0`). `scripts/update_version.py` propagates it to the places that must agree
(`pyproject.toml`, the Helm `Chart.yaml` version and `appVersion`). `CHANGELOG.md`
records the human-readable history.

Before cutting a release, confirm `VERSION`, `pyproject.toml`, and
`charts/faster-whisper-server/Chart.yaml` all match, and that `CHANGELOG.md` has an
entry for the version.

## Release workflow

Releases are driven by `.github/workflows/release.yml`. It is
**`workflow_dispatch`-only** (manual). Inputs:

- `version` (required) — creates the tag `v<version>`.
- `publish_jetson` (default `true`) — also build and push the Jetson image.
- `validate_only` (default `false`) — push version-tagged images only; no
  `:latest`, no GitHub Release.

What it does:

1. **build-amd64** — builds `docker/Dockerfile` for `linux/amd64` and pushes
   `…-cu128:<version>` plus the unsuffixed `…:<version>` alias (and the `latest`
   aliases on a real release).
2. **build-jetson** — on an arm64 runner, builds `docker/jetson/Dockerfile` for
   `linux/arm64` and pushes `…-jetson:<version>` (gated on `publish_jetson`).
3. **smoke-amd64** — boots the published amd64 image on CPU
   (`DEVICE=cpu COMPUTE_TYPE=int8 MODEL_SIZE=tiny`, offline) and asserts `/health`,
   `/ready`, auth (401 without key / 200 with), and a real transcription of
   `docker/jfk.flac`.
4. **publish-chart** — `helm package` the chart with the release version and
   `helm push` it to `oci://ghcr.io/forgeguard-ai/charts`.
5. **create-release** — creates/updates the GitHub Release `v<version>` (skipped
   when `validate_only` is true).

## Image tags produced

- `ghcr.io/forgeguard-ai/faster-whisper-server-cu128:<version>` and the
  unsuffixed `…:<version>` alias, plus their `latest` aliases on a real release.
- `ghcr.io/forgeguard-ai/faster-whisper-server-jetson:<version>` and its `latest`.

## Chart

The chart is published as an OCI artifact at
`oci://ghcr.io/forgeguard-ai/charts/faster-whisper-server` with `version` and
`appVersion` equal to the release version. Install with
`helm install whisper oci://ghcr.io/forgeguard-ai/charts/faster-whisper-server --version <version>`.

## Pre-release checklist

1. `uv run --extra test pytest tests/` and `uv run --extra test ruff check .` pass.
2. `VERSION`, `pyproject.toml`, and `Chart.yaml` agree; `CHANGELOG.md` updated.
3. The affected images build.
4. Run the release workflow with `validate_only: true` first if you want to test
   the build/push path without cutting a public release.
