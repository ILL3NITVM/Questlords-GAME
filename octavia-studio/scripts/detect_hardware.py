"""Hardware and capability detection (section 15).

Reports what the machine can actually run and recommends a model class. It
never downloads anything — recommendations only.
"""
from __future__ import annotations

import json
import os
import pathlib
import platform
import shutil
import subprocess
from typing import Any, Dict, List, Optional


def _cmd(args: List[str], timeout: int = 6) -> Optional[str]:
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return out.stdout.strip() if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def detect_gpu() -> Dict[str, Any]:
    info: Dict[str, Any] = {"vendor": None, "devices": [], "vram_mb": 0}

    nv = _cmd(["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
               "--format=csv,noheader,nounits"])
    if nv:
        info["vendor"] = "nvidia"
        for line in nv.splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 2:
                try:
                    vram = int(float(parts[1]))
                except ValueError:
                    vram = 0
                info["devices"].append({"name": parts[0], "vram_mb": vram,
                                        "driver": parts[2] if len(parts) > 2 else ""})
                info["vram_mb"] = max(info["vram_mb"], vram)
        return info

    if platform.system() == "Darwin":
        chip = _cmd(["sysctl", "-n", "machdep.cpu.brand_string"]) or ""
        if "Apple" in chip:
            info["vendor"] = "apple_silicon"
            info["devices"].append({"name": chip, "vram_mb": 0,
                                    "note": "unified memory — MPS backend"})
            return info

    rocm = _cmd(["rocm-smi", "--showmeminfo", "vram"])
    if rocm:
        info["vendor"] = "amd"
        info["devices"].append({"name": "AMD ROCm device", "vram_mb": 0})
    return info


def detect_memory() -> Dict[str, Any]:
    total_mb = 0
    try:
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemTotal:"):
                    total_mb = int(line.split()[1]) // 1024
                    break
    except OSError:
        page = os.sysconf("SC_PAGE_SIZE") if hasattr(os, "sysconf") else 0
        pages = os.sysconf("SC_PHYS_PAGES") if hasattr(os, "sysconf") else 0
        total_mb = (page * pages) // (1024 * 1024) if page and pages else 0
    return {"total_mb": total_mb}


def detect_storage(path: pathlib.Path) -> Dict[str, Any]:
    usage = shutil.disk_usage(path)
    return {"total_gb": round(usage.total / 2**30, 1),
            "free_gb": round(usage.free / 2**30, 1)}


def recommend_models(gpu: Dict[str, Any], mem: Dict[str, Any],
                     storage: Dict[str, Any]) -> Dict[str, Any]:
    vram = gpu.get("vram_mb", 0)
    vendor = gpu.get("vendor")
    free = storage.get("free_gb", 0)

    if vendor is None:
        tier = "cpu_only"
        rec = ["No GPU detected. Local diffusion on CPU is impractical "
               "(minutes to tens of minutes per image).",
               "Use renderer.backend='api' against a hosted endpoint, or run this "
               "studio on a machine with a GPU."]
        classes: List[str] = []
    elif vendor == "apple_silicon":
        tier = "apple_silicon"
        rec = ["Apple Silicon via MPS works but is slower than CUDA.",
               "SDXL-class models are realistic; Flux-class will be slow."]
        classes = ["SDXL 1.0 + photoreal fine-tune", "SD 1.5 + photoreal fine-tune"]
    elif vram >= 22000:
        tier = "high"
        rec = ["Ample VRAM. Flux.1-dev or SDXL at high resolution with "
               "refiners, IPAdapter and ControlNet loaded together."]
        classes = ["Flux.1-dev (~24GB)", "SDXL 1.0 + photoreal fine-tune (~7GB)",
                   "SDXL refiner (~6GB)"]
    elif vram >= 14000:
        tier = "good"
        rec = ["Comfortable for SDXL-class photoreal work with IPAdapter/InstantID.",
               "Flux.1-dev needs quantisation (fp8/GGUF) at this VRAM."]
        classes = ["SDXL 1.0 + photoreal fine-tune", "Flux.1-dev fp8 quantised"]
    elif vram >= 10000:
        tier = "moderate"
        rec = ["SDXL will fit but expect tight headroom with ControlNet + IPAdapter.",
               "Generate at 896x1152 rather than higher, then upscale separately."]
        classes = ["SDXL 1.0 + photoreal fine-tune", "SD 1.5 + photoreal fine-tune"]
    elif vram >= 6000:
        tier = "low"
        rec = ["SD 1.5-class photoreal models are the practical ceiling.",
               "SDXL may run with --lowvram but will be slow."]
        classes = ["SD 1.5 + photoreal fine-tune"]
    else:
        tier = "insufficient"
        rec = ["Insufficient VRAM for comfortable local generation. Prefer a hosted API backend."]
        classes = []

    warnings: List[str] = []
    if free < 30 and classes:
        warnings.append(f"Only {free} GB free. A working SDXL setup with "
                        "IPAdapter, ControlNet and an upscaler needs roughly 30-50 GB.")
    if mem.get("total_mb", 0) < 16000 and classes:
        warnings.append("Under 16 GB system RAM — model loading may thrash.")

    return {"tier": tier, "recommendations": rec, "model_classes": classes,
            "warnings": warnings,
            "note": "Nothing is downloaded automatically. Install models yourself, "
                    "or ask the studio operator to confirm before fetching."}


def full_report(project_root: pathlib.Path) -> Dict[str, Any]:
    gpu = detect_gpu()
    mem = detect_memory()
    storage = detect_storage(project_root)
    return {
        "platform": {"system": platform.system(), "release": platform.release(),
                     "python": platform.python_version(), "machine": platform.machine()},
        "cpu_count": os.cpu_count(),
        "memory": mem,
        "gpu": gpu,
        "storage": storage,
        "advice": recommend_models(gpu, mem, storage),
    }


if __name__ == "__main__":
    print(json.dumps(full_report(pathlib.Path.cwd()), indent=2))
