"""Tests for the model readiness state machine, /health + /ready semantics,
and the 503 warming guard on inference routes.

IMPORTANT: never let the real warmup run inside `with TestClient(app)` — a
failed warmup calls os._exit(1), which would kill the pytest process. Every
lifespan-entering test patches server.transcription.get_model.
"""

import asyncio
import threading
import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from server import config, model_status
from server.main import _warmup, app
from server.model_status import ModelStatus

# Module-scope client: no `with`, so lifespan never runs and the state stays
# UNINITIALIZED for the non-lifespan tests below.
client = TestClient(app)

AUTH = {"Authorization": "Bearer test-key"}  # conftest sets API_KEY=test-key


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------


def test_initial_state_uninitialized():
    assert model_status.get_status() is ModelStatus.UNINITIALIZED
    assert model_status.get_error() is None
    assert model_status.get_metadata() == {}


def test_transitions():
    model_status.set_warming()
    assert model_status.get_status() is ModelStatus.WARMING

    model_status.set_ready("cpu", "int8", "tiny")
    assert model_status.get_status() is ModelStatus.READY
    assert model_status.get_metadata() == {
        "device": "cpu",
        "compute_type": "int8",
        "model": "tiny",
    }

    model_status.set_failed("boom")
    assert model_status.get_status() is ModelStatus.FAILED
    assert model_status.get_error() == "boom"
    assert model_status.get_metadata() == {}

    model_status.reset()
    assert model_status.get_status() is ModelStatus.UNINITIALIZED


# ---------------------------------------------------------------------------
# /health and /ready per state (no lifespan)
# ---------------------------------------------------------------------------


def test_health_uninitialized():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {
        "status": "healthy",
        "model_loaded": False,
        "device": None,
        "compute_type": None,
        "model": None,
    }


def test_health_warming():
    model_status.set_warming()
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "warming", "model_loaded": False}


def test_health_ready():
    model_status.set_ready("cpu", "int8", "tiny")
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {
        "status": "healthy",
        "model_loaded": True,
        "device": "cpu",
        "compute_type": "int8",
        "model": "tiny",
    }


def test_health_failed():
    model_status.set_failed("model exploded")
    r = client.get("/health")
    assert r.status_code == 503
    assert r.json() == {"status": "failed", "error": "model exploded"}


def test_ready_only_when_ready():
    for state_setter, expected in [
        (lambda: None, 503),  # UNINITIALIZED
        (model_status.set_warming, 503),
        (lambda: model_status.set_ready("cpu", "int8", "tiny"), 200),
        (lambda: model_status.set_failed("x"), 503),
    ]:
        model_status.reset()
        state_setter()
        r = client.get("/ready")
        assert r.status_code == expected
        if expected == 503:
            assert r.headers["Retry-After"] == "10"


# ---------------------------------------------------------------------------
# Warming guard on inference routes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    ["/v1/audio/transcriptions", "/v1/audio/translations"],
)
def test_inference_routes_503_while_warming(path):
    """Auth passes (valid key); the readiness guard fires before body validation."""
    model_status.set_warming()
    r = client.post(path, headers=AUTH)
    assert r.status_code == 503
    assert r.json()["detail"]["error"] == "model_warming"
    assert r.headers["Retry-After"] == "10"


def test_inference_routes_503_when_failed():
    model_status.set_failed("no weights")
    r = client.post("/v1/audio/transcriptions", headers=AUTH)
    assert r.status_code == 503
    assert r.json()["detail"]["error"] == "model_failed"
    assert "Retry-After" not in r.headers  # failed is terminal, no retry hint


def test_guard_passes_when_ready():
    """When READY the guard lets the request through to normal validation
    (422 on a missing file proves we got past the 503 gate without loading a model)."""
    model_status.set_ready("cpu", "int8", "tiny")
    r = client.post("/v1/audio/transcriptions", headers=AUTH)
    assert r.status_code == 422


def test_warming_503_carries_openai_error_envelope():
    """The envelope adds body.error for OpenAI SDKs while keeping detail intact
    (the web console parses detail.error == 'model_warming')."""
    model_status.set_warming()
    r = client.post("/v1/audio/transcriptions", headers=AUTH)
    assert r.status_code == 503
    body = r.json()
    assert body["detail"]["error"] == "model_warming"
    assert body["error"] == {
        "message": "STT model is still loading; retry shortly.",
        "type": "server_error",
        "code": 503,
    }


def test_lazy_load_flips_readiness(monkeypatch):
    """With warmup skipped (state UNINITIALIZED), the first request's lazy load
    must flip /ready to 200."""
    from server import model_manager

    class _FakeInfo:
        language = "en"
        duration = 0.0

    class _FakeModel:
        def transcribe(self, *args, **kwargs):
            return iter(()), _FakeInfo()

    model_manager.reset()
    monkeypatch.setattr(model_manager, "WhisperModel", lambda *a, **k: _FakeModel())
    try:
        assert client.get("/ready").status_code == 503  # UNINITIALIZED

        r = client.post(
            "/v1/audio/transcriptions",
            headers=AUTH,
            files={"file": ("a.wav", b"x")},
            data={"response_format": "json"},
        )
        assert r.status_code == 200

        assert model_status.get_status() is ModelStatus.READY
        assert client.get("/ready").status_code == 200
    finally:
        # Never leak the fake model into the manager for the real-inference tests.
        model_manager.reset()


def test_models_open_while_warming():
    """/v1/models has no readiness dependency, so it answers during warmup."""
    model_status.set_warming()
    r = client.get("/v1/models", headers=AUTH)
    assert r.status_code == 200
    assert r.json()["object"] == "list"


# ---------------------------------------------------------------------------
# Auth interaction: 401 wins over warming 503; health/ready stay open
# ---------------------------------------------------------------------------


def test_auth_beats_warming_503():
    model_status.set_warming()
    # health/ready are unauthenticated
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 503  # open, but not ready

    # missing key -> 401 even though the model is warming
    r = client.post("/v1/audio/transcriptions")
    assert r.status_code == 401

    # valid key -> the warming 503 surfaces
    r = client.post("/v1/audio/transcriptions", headers=AUTH)
    assert r.status_code == 503
    assert r.json()["detail"]["error"] == "model_warming"


# ---------------------------------------------------------------------------
# Lifespan behavior
# ---------------------------------------------------------------------------


def _patched_get_model(release: threading.Event):
    """Patch get_model with a warmup that completes only once `release` is set.

    A threading.Event polled from the threadpool keeps the signal thread-safe
    (TestClient runs the app loop, and thus run_in_threadpool, in a worker thread).
    """

    def fake_get_model():
        while not release.is_set():
            time.sleep(0.01)
        return object()

    return patch("server.transcription.get_model", new=fake_get_model)


def _wait_for_healthy(c: TestClient, timeout: float = 5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        body = c.get("/health").json()
        if body["status"] == "healthy" and body["model_loaded"]:
            return body
        time.sleep(0.02)
    raise AssertionError("server never reported healthy/model_loaded")


def test_lifespan_serves_while_warming_then_ready():
    release = threading.Event()
    with _patched_get_model(release):
        with TestClient(app) as c:
            # Serving immediately, still warming
            r = c.get("/health")
            assert r.status_code == 200
            assert r.json() == {"status": "warming", "model_loaded": False}
            assert c.get("/ready").status_code == 503

            release.set()
            _wait_for_healthy(c)
            assert c.get("/ready").status_code == 200


def test_lifespan_warmup_disabled(monkeypatch):
    monkeypatch.setattr(config, "WARMUP_ON_START", False)
    release = threading.Event()
    release.set()
    with _patched_get_model(release):
        with TestClient(app) as c:
            r = c.get("/health")
            assert r.status_code == 200
            body = r.json()
            assert body["status"] == "healthy"
            assert body["model_loaded"] is False
            assert model_status.get_status() is ModelStatus.UNINITIALIZED


def test_lifespan_shutdown_cancels_pending_warmup():
    release = threading.Event()  # never set: warmup stays pending
    try:
        with _patched_get_model(release):
            with TestClient(app) as c:
                assert c.get("/health").json()["status"] == "warming"
            # exiting the context runs shutdown; the pending task must be
            # cancelled without hanging or raising
        assert app.state.warmup_task.cancelled()
    finally:
        release.set()  # unblock the stray warmup thread


# ---------------------------------------------------------------------------
# Failure path
# ---------------------------------------------------------------------------


class _Exit(Exception):
    def __init__(self, code):
        self.code = code


def test_warmup_failure_sets_failed_and_exits(monkeypatch):
    def fake_exit(code):
        raise _Exit(code)

    monkeypatch.setattr("os._exit", fake_exit)

    def boom():
        raise RuntimeError("no weights")

    with patch("server.transcription.get_model", new=boom):
        with pytest.raises(_Exit) as exc_info:
            asyncio.run(_warmup(app))

    assert exc_info.value.code == 1
    assert model_status.get_status() is ModelStatus.FAILED
    assert "no weights" in model_status.get_error()
