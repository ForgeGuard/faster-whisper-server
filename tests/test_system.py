"""The /system telemetry endpoint: open, and the expected metadata shape."""

from fastapi.testclient import TestClient

from server.main import app

client = TestClient(app)


def test_system_is_open_and_well_shaped():
    # Telemetry is unauthenticated (like /health) so the console monitor renders
    # before a key is entered.
    r = client.get("/system")
    assert r.status_code == 200
    body = r.json()

    for key in ("version", "state", "device", "compute_type", "model", "gpu", "activity", "models"):
        assert key in body, f"missing {key}"

    # Activity counters are always present integers.
    assert body["activity"]["active"] == 0
    assert body["activity"]["waiting"] == 0

    # GPU is either null (no driver, e.g. CI) or a dict with memory totals.
    assert body["gpu"] is None or "memory_total_bytes" in body["gpu"]

    # Model presets carry active/loaded flags.
    models = body["models"]
    assert models["active"]  # the configured/persisted size
    assert isinstance(models["presets"], list)
    assert any(p.get("is_active") for p in models["presets"])


def test_gpu_info_degrades_without_driver(monkeypatch):
    import builtins

    from server import system

    # Simulate NVML unavailable (no nvidia-ml-py / no driver): gpu_info is None.
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pynvml":
            raise ImportError("no pynvml")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert system.gpu_info() is None
