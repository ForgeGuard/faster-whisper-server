#!/usr/bin/env python3
"""Download a CTranslate2 Whisper model into the baked-model dir at image build time.

Run during the Docker build to bake the image's default model into
``<output>/<model>`` (e.g. ``/app/models/large-v3``). The runtime resolver
(``server.provisioning.resolve_model``) picks that directory up when
``MODEL_DIR`` points at ``<output>`` and ``MODEL_SIZE`` matches ``<model>``.

The trusted revision is resolved through ``server.provisioning`` so the pin
table has a single source of truth shared with the running server. Only the
canonical Systran repos we vet are auto-pinned; a custom model id or an explicit
``--revision`` / ``MODEL_REVISION`` bypasses the built-in pins.

Usage:
    download_model.py --model <size-or-repo> --output <dir> [--revision REV]

Environment:
    MODEL_REVISION            fallback for --revision
    MODEL_DOWNLOAD_RETRIES    download attempts (default 4)
"""

import argparse
import json
import os
import shutil
import sys
import time

# Make ``server.provisioning`` importable both in the image (app at /app) and in
# a source checkout (repo root two levels up from docker/scripts/).
sys.path.insert(0, "/app")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from faster_whisper import download_model as fw_download  # noqa: E402

from server.provisioning import canonical_repo, resolve_revision  # noqa: E402

# Files a valid CTranslate2 Whisper model directory must contain. model.bin is
# the one the runtime resolver also checks; the other two catch a truncated
# download.
_REQUIRED = ("model.bin", "config.json", "tokenizer.json")


def _valid(dest: str) -> bool:
    return all(
        os.path.isfile(os.path.join(dest, name))
        and os.path.getsize(os.path.join(dest, name)) > 0
        for name in _REQUIRED
    )


def provision(model: str, output: str, revision_override: str) -> str:
    # The directory name MUST equal the runtime MODEL_SIZE string.
    dest = os.path.join(output, model)
    if _valid(dest):
        print(f"Model already present and valid: {dest}", file=sys.stderr)
        return dest

    revision = resolve_revision(model, revision_override or None)
    repo = canonical_repo(model)
    retries = int(os.getenv("MODEL_DOWNLOAD_RETRIES", "4"))
    os.makedirs(dest, exist_ok=True)

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            print(
                f"Downloading model={model} repo={repo} revision={revision} "
                f"-> {dest} (attempt {attempt}/{retries})",
                file=sys.stderr,
            )
            fw_download(model, output_dir=dest, revision=revision)
            break
        except Exception as exc:  # noqa: BLE001 — retry any transient hub error
            last_error = exc
            print(f"  download failed: {exc}", file=sys.stderr)
            if attempt < retries:
                time.sleep(2 ** attempt)
    else:
        raise RuntimeError(f"Failed to download model {model}: {last_error}")

    if not _valid(dest):
        raise RuntimeError(f"Downloaded model failed verification: {dest}")

    # snapshot_download leaves a .cache/ of hub metadata in the target dir; drop
    # it so the baked image layer only carries the actual model files.
    shutil.rmtree(os.path.join(dest, ".cache"), ignore_errors=True)

    with open(os.path.join(dest, ".provenance.json"), "w", encoding="utf-8") as handle:
        json.dump({"model": model, "repo": repo, "revision": revision}, handle)
    print(f"Model ready: {dest}", file=sys.stderr)
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="model size alias or HF repo id")
    parser.add_argument("--output", required=True, help="baked-model root dir (MODEL_DIR)")
    parser.add_argument(
        "--revision",
        default=os.getenv("MODEL_REVISION", ""),
        help="HF git revision override (default: $MODEL_REVISION, else built-in pin)",
    )
    args = parser.parse_args()
    provision(args.model, args.output, args.revision)


if __name__ == "__main__":
    main()
