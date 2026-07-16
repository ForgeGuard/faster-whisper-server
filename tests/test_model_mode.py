"""Model-mode: preset listing, auth-guarded activate, and persistence."""

import pytest
from fastapi.testclient import TestClient

from server import config, model_manager, model_status
from server.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer test-key"}  # conftest sets API_KEY=test-key


class _FakeInfo:
    language = "en"
    duration = 0.0


class _FakeModel:
    def transcribe(self, *args, **kwargs):
        return iter(()), _FakeInfo()


@pytest.fixture
def isolated_data_dir(tmp_path, monkeypatch):
    """Point persistence at a temp dir and reset manager state around the test."""
    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    model_manager.reset()
    monkeypatch.setattr(model_manager, "WhisperModel", lambda *a, **k: _FakeModel())
    yield tmp_path
    model_manager.reset()


def test_presets_info_shape():
    info = model_manager.presets_info()
    assert "active" in info and "loaded" in info and "presets" in info
    sizes = {p["size"] for p in info["presets"]}
    assert {"tiny", "small", "large-v3", "large-v3-turbo"} <= sizes


def test_turbo_is_a_selectable_size():
    # Whisper "turbo" is in the catalog and accepted by the activate guard.
    assert model_manager.is_valid_size("large-v3-turbo")
    labels = {p["size"]: p["label"] for p in model_manager.PRESETS}
    assert labels["large-v3-turbo"] == "Large v3 Turbo"


def test_presets_endpoint_lists_active(isolated_data_dir):
    r = client.get("/api/model/presets", headers=AUTH)
    assert r.status_code == 200
    assert r.json()["active"] == config.MODEL_SIZE  # "tiny" in tests


def test_activate_requires_auth():
    r = client.post("/api/model/activate", json={"size": "tiny"})
    assert r.status_code == 401


def test_activate_rejects_unknown_size(isolated_data_dir):
    r = client.post("/api/model/activate", headers=AUTH, json={"size": "gargantuan"})
    assert r.status_code == 400
    assert r.json()["detail"]["error"] == "invalid_model"


def test_activate_switches_and_persists(isolated_data_dir):
    r = client.post("/api/model/activate", headers=AUTH, json={"size": "small"})
    assert r.status_code == 200
    body = r.json()
    assert body["active"] == "small"
    assert body["loaded"] == "small"

    # Persisted to <DATA_DIR>/active_model.
    persisted = (isolated_data_dir / "active_model").read_text().strip()
    assert persisted == "small"

    # A fresh manager (simulating a restart) resumes the persisted choice.
    model_manager.reset()
    assert model_manager.active_model() == "small"

    # And readiness metadata reflects the switched size.
    assert model_status.get_metadata()["model"] == "small"
