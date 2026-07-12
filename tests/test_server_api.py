"""Server-layer tests for the OpenAI-compatible API.

Env is set in conftest.py (CPU/int8 tiny model, API_KEY=test-key). The
transcription/translation tests do a real tiny-model inference of docker/jfk.flac;
with no lifespan the model state stays UNINITIALIZED, which passes the readiness
gate and lazy-loads on first request.
"""

import asyncio
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from server.main import app

SAMPLE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docker", "jfk.flac")
client = TestClient(app)


def _auth():
    return {"Authorization": "Bearer test-key"}


def test_health_and_ready_are_open():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {
        "status": "healthy",
        "model_loaded": False,
        "device": None,
        "compute_type": None,
        "model": None,
    }
    r = client.get("/ready")
    assert r.status_code == 503
    assert r.headers["Retry-After"] == "10"


def test_requires_api_key():
    r = client.post("/v1/audio/transcriptions", files={"file": ("a.wav", b"x")})
    assert r.status_code == 401


def test_non_ascii_bearer_token_is_401_not_500():
    # secrets.compare_digest raises TypeError on non-ASCII str inputs; the
    # comparison must run on bytes so a weird token is a clean 401.
    r = client.post(
        "/v1/audio/transcriptions",
        # latin-1 bytes: what a browser puts on the wire (httpx would reject
        # a non-ASCII str header value client-side).
        headers={b"Authorization": "Bearer café".encode("latin-1")},
        files={"file": ("a.wav", b"x")},
    )
    assert r.status_code == 401


def test_unsupported_language_is_400():
    r = client.post(
        "/v1/audio/transcriptions",
        headers=_auth(),
        files={"file": ("a.wav", b"x")},
        data={"language": "zz"},
    )
    assert r.status_code == 400
    assert "Unsupported language: zz" in r.json()["detail"]


def test_spool_cleanup_on_read_failure(tmp_path, monkeypatch):
    """A mid-upload failure (client disconnect etc.) must not orphan the temp file."""
    from server import transcription

    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))

    class FailingUpload:
        size = None

        def __init__(self):
            self.calls = 0

        async def read(self, n):
            self.calls += 1
            if self.calls == 1:
                return b"x" * 16
            raise RuntimeError("client went away")

    with pytest.raises(RuntimeError):
        asyncio.run(transcription._spool_upload(FailingUpload(), ".wav"))
    assert list(tmp_path.iterdir()) == []


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
    # OpenAI wire name: array-style `timestamp_granularities[]` form field.
    with open(SAMPLE, "rb") as f:
        r = client.post(
            "/v1/audio/transcriptions",
            headers=_auth(),
            files={"file": ("jfk.flac", f, "audio/flac")},
            data={
                "response_format": "verbose_json",
                "timestamp_granularities[]": ["word"],
            },
        )
    assert r.status_code == 200
    body = r.json()
    assert body["task"] == "transcribe"
    assert body["segments"] and "no_speech_prob" in body["segments"][0]
    # Word timings live only in the flattened top-level list (OpenAI shape).
    assert "words" not in body["segments"][0]
    assert body["words"] and "probability" in body["words"][0]


def test_bare_timestamp_granularities_name_also_accepted():
    with open(SAMPLE, "rb") as f:
        r = client.post(
            "/v1/audio/transcriptions",
            headers=_auth(),
            files={"file": ("jfk.flac", f, "audio/flac")},
            data={
                "response_format": "verbose_json",
                "timestamp_granularities": ["word"],
            },
        )
    assert r.status_code == 200
    body = r.json()
    assert body["words"] and "probability" in body["words"][0]


def test_srt_format():
    with open(SAMPLE, "rb") as f:
        r = client.post(
            "/v1/audio/transcriptions",
            headers=_auth(),
            files={"file": ("jfk.flac", f, "audio/flac")},
            data={"response_format": "srt"},
        )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    blocks = r.text.strip().split("\n\n")
    assert blocks[0].startswith("1\n")
    first_cue = blocks[0].split("\n")[1]
    # HH:MM:SS,mmm --> HH:MM:SS,mmm
    assert " --> " in first_cue
    start, end = first_cue.split(" --> ")
    for stamp in (start, end):
        assert len(stamp) == 12 and stamp[8] == ","
    assert "country" in r.text.lower()


def test_vtt_format():
    with open(SAMPLE, "rb") as f:
        r = client.post(
            "/v1/audio/transcriptions",
            headers=_auth(),
            files={"file": ("jfk.flac", f, "audio/flac")},
            data={"response_format": "vtt"},
        )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    assert r.text.startswith("WEBVTT\n\n")
    cue = r.text.split("\n\n")[1].split("\n")[0]
    start, end = cue.split(" --> ")
    for stamp in (start, end):
        assert len(stamp) == 12 and stamp[8] == "."
    assert "country" in r.text.lower()


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


def test_error_envelope_on_400():
    """HTTPExceptions carry an OpenAI-shaped `error` object plus the raw `detail`."""
    r = client.post(
        "/v1/audio/transcriptions",
        headers=_auth(),
        files={"file": ("a.wav", b"x")},
        data={"response_format": "bogus"},
    )
    assert r.status_code == 400
    body = r.json()
    assert body["detail"] == "Unsupported response_format"
    assert body["error"] == {
        "message": "Unsupported response_format",
        "type": "invalid_request_error",
        "code": 400,
    }


# ---------------------------------------------------------------------------
# Web console serving (router + /web/assets StaticFiles mount, as in main.py)
# ---------------------------------------------------------------------------


def _web_client(monkeypatch, tmp_path) -> TestClient:
    """Standalone app mirroring main.py's web wiring against a temp dist dir.

    conftest disables ENABLE_WEB_UI for the main app, so the /web surface is
    exercised on its own app here.
    """
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles

    from server import config, web

    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>console</html>")
    (dist / "assets" / "app.js").write_text("console.log('hi')")

    monkeypatch.setattr(config, "WEBUI_DIST_DIR", str(dist))
    web_app = FastAPI()
    web_app.mount(
        "/web/assets",
        StaticFiles(directory=str(dist / "assets"), check_dir=False),
        name="web-assets",
    )
    web_app.include_router(web.router)
    return TestClient(web_app)


def test_web_slashless_redirects_to_trailing_slash(monkeypatch, tmp_path):
    # The SPA is built with relative asset URLs (Vite base './'), so /web must
    # redirect to /web/ or the assets resolve against the site root and 404.
    c = _web_client(monkeypatch, tmp_path)
    r = c.get("/web", follow_redirects=False)
    assert r.status_code == 308
    assert r.headers["location"] == "/web/"


def test_web_config_payload(monkeypatch, tmp_path):
    from server import config
    from server.version import __version__

    c = _web_client(monkeypatch, tmp_path)
    body = c.get("/web/config").json()
    assert body == {
        "version": __version__,
        "root_path": os.environ.get("UVICORN_ROOT_PATH", ""),
        "max_upload_bytes": config.MAX_UPLOAD_BYTES,
        "model": config.MODEL_SIZE,
    }


def test_web_serves_index_and_spa_fallback(monkeypatch, tmp_path):
    c = _web_client(monkeypatch, tmp_path)
    assert c.get("/web/").text == "<html>console</html>"
    # Unknown extensionless paths are SPA client routes -> index.html.
    r = c.get("/web/some/route")
    assert r.status_code == 200
    assert r.text == "<html>console</html>"


def test_web_missing_asset_is_404_not_spa_fallback(monkeypatch, tmp_path):
    c = _web_client(monkeypatch, tmp_path)
    assert c.get("/web/assets/nope.js").status_code == 404
    # Dotted basenames outside /web/assets also 404 instead of serving HTML.
    assert c.get("/web/favicon.ico").status_code == 404


def test_web_assets_support_conditional_requests(monkeypatch, tmp_path):
    c = _web_client(monkeypatch, tmp_path)
    r = c.get("/web/assets/app.js")
    assert r.status_code == 200
    etag = r.headers["etag"]
    r304 = c.get("/web/assets/app.js", headers={"If-None-Match": etag})
    assert r304.status_code == 304
