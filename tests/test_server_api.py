"""Server-layer tests for the OpenAI-compatible API.

Env is set in conftest.py (CPU/int8 tiny model, API_KEY=test-key). The
transcription/translation tests do a real tiny-model inference of docker/jfk.flac;
with no lifespan the model state stays UNINITIALIZED, which passes the readiness
gate and lazy-loads on first request.
"""

import os

from fastapi.testclient import TestClient

from server.main import app

SAMPLE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docker", "jfk.flac")
client = TestClient(app)


def _auth():
    return {"Authorization": "Bearer test-key"}


def test_health_and_ready_are_open():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy", "model_loaded": False}
    r = client.get("/ready")
    assert r.status_code == 503
    assert r.headers["Retry-After"] == "10"


def test_requires_api_key():
    r = client.post("/v1/audio/transcriptions", files={"file": ("a.wav", b"x")})
    assert r.status_code == 401


def test_models_endpoint_auth_pair():
    assert client.get("/v1/models").status_code == 401
    r = client.get("/v1/models", headers=_auth())
    assert r.status_code == 200
    ids = [m["id"] for m in r.json()["data"]]
    assert "whisper-1" in ids and "tiny" in ids


def test_text_format_returns_plain_text():
    with open(SAMPLE, "rb") as f:
        r = client.post(
            "/v1/audio/transcriptions",
            headers=_auth(),
            files={"file": ("jfk.flac", f, "audio/flac")},
            data={"response_format": "text"},
        )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    assert "country" in r.text.lower()


def test_verbose_json_includes_words():
    with open(SAMPLE, "rb") as f:
        r = client.post(
            "/v1/audio/transcriptions",
            headers=_auth(),
            files={"file": ("jfk.flac", f, "audio/flac")},
            data={"response_format": "verbose_json", "timestamp_granularities": ["word"]},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["task"] == "transcribe"
    assert body["segments"] and "no_speech_prob" in body["segments"][0]
    assert body["words"] and "probability" in body["words"][0]


def test_translation_endpoint_returns_english():
    with open(SAMPLE, "rb") as f:
        r = client.post(
            "/v1/audio/translations",
            headers=_auth(),
            files={"file": ("jfk.flac", f, "audio/flac")},
            data={"response_format": "text"},
        )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    # jfk.flac is English; translation to English still returns the phrase.
    assert "country" in r.text.lower()
