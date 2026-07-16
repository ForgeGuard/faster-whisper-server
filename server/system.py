"""Live system telemetry: GPU utilization/memory/temp/power + request activity.

Surfaced on an unauthenticated ``/system`` endpoint (telemetry only, no PII —
open like ``/health`` so the console's monitor renders before any key is
entered). GPU metrics are best-effort via NVML (``nvidia-ml-py``): this stack
has no torch, so memory comes from NVML too, and each metric degrades
independently so a driver that omits one does not drop the rest. When no GPU /
driver is present, ``gpu`` is ``null``.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from server import activity, config, model_status
from server.version import __version__

router = APIRouter()


def gpu_info() -> dict[str, Any] | None:
    """Live GPU telemetry via NVML, or None when no GPU/driver is available."""
    try:
        import pynvml
    except ImportError:
        return None
    try:
        pynvml.nvmlInit()
    except Exception:  # no driver in this namespace / not a GPU host
        return None
    try:
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        info: dict[str, Any] = {}
        try:
            name = pynvml.nvmlDeviceGetName(handle)
            info["name"] = name.decode() if isinstance(name, bytes) else name
        except Exception:
            info["name"] = "GPU"
        try:
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            info["memory_used_bytes"] = int(mem.used)
            info["memory_total_bytes"] = int(mem.total)
        except Exception:
            pass
        try:
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            info["utilization_pct"] = int(util.gpu)
            info["memory_utilization_pct"] = int(util.memory)
        except Exception:
            pass
        try:
            info["temperature_c"] = int(
                pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            )
        except Exception:
            pass
        try:
            info["power_w"] = round(pynvml.nvmlDeviceGetPowerUsage(handle) / 1000, 1)
        except Exception:
            pass
        try:
            info["power_limit_w"] = round(
                pynvml.nvmlDeviceGetEnforcedPowerLimit(handle) / 1000, 1
            )
        except Exception:
            pass
        # A GPU with no readable memory info at all is not useful telemetry.
        return info if "memory_total_bytes" in info else None
    finally:
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass


@router.get("/system")
async def system_info() -> dict[str, Any]:
    from server import model_manager

    meta = model_status.get_metadata()
    return {
        "version": __version__,
        "state": model_status.get_status().value,
        "device": config.DEVICE,
        "compute_type": meta.get("compute_type") or config.COMPUTE_TYPE,
        "model": model_manager.active_model(),
        "gpu": gpu_info(),
        "activity": activity.activity_info(),
        "models": model_manager.presets_info(),
    }
