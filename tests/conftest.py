"""Shared test configuration.

These env vars must be set before any test module imports ``server.*`` — the
config module reads them once at import time. A CPU/int8 tiny model keeps the
suite fast and hardware-independent; MODEL_DIR="" forces the hub download path so
dev boxes without a baked ``/app/models`` still resolve a model.
"""

import os

os.environ.setdefault("DEVICE", "cpu")
os.environ.setdefault("MODEL_SIZE", "tiny")
os.environ.setdefault("COMPUTE_TYPE", "int8")
os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("ENABLE_WEB_UI", "false")
os.environ.setdefault("MODEL_DIR", "")

import pytest  # noqa: E402

from server import model_status  # noqa: E402


@pytest.fixture(autouse=True)
def reset_model_status():
    """Module-level model state must never leak between tests."""
    model_status.reset()
    yield
    model_status.reset()
